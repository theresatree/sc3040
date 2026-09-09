from fastapi import HTTPException
import cv2
import numpy as np
import supervision as sv

from datetime import datetime, timedelta

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from trackers import ByteTrackTracker
from app.auth.dependencies import get_current_user_ws, require_admin
from app.auth.embeddings import derive_user_key, generate_iom_projection
from app.db.database import get_db
from app.db.enums import DayOfWeek
from app.db.models import Attendance, Registered, Timetable
from app.ml.checkin import CheckInProcessor, match_kps
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.db.models import User

router = APIRouter(
    prefix="/attendance",
    tags=["attendance"],
)

GRACE_PERIOD = 15
GRACE_DISTANCE = 25  # meters


async def record_attendance( db: AsyncSession, user_id: int, latitude: float, longitude: float) -> int | None:
    now = datetime.utcnow()
    today = now.date()
    current_time = now.time()

    result = await db.execute(
        select(Timetable)
        .options(joinedload(Timetable.room))
        .join(Registered, Registered.timetable_id == Timetable.id)
        .where(Registered.user_id == user_id)
    )
    timetables = result.scalars().all()

    if len(timetables) == 0:
        return None

    current_day = list(DayOfWeek)[now.weekday()]

    chosen = next(
        (
            t
            for t in timetables
            if t.day_of_week == current_day
            and t.start <= current_time <= t.end
        ),
        None,
    )

    if chosen is None:
        raise HTTPException(
            status_code=404,
            detail="No class",
        )

    grace_end = (
        datetime.combine(today, chosen.start)
        + timedelta(minutes=GRACE_PERIOD)
    ).time()

    if current_time > grace_end:
        raise HTTPException(
            status_code=400,
            detail="Grace period up",
        )

    user_point = cast(
        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
        Geography(geometry_type="POINT", srid=4326),
    )

    distance = await db.scalar(
        select(func.ST_Distance(user_point, chosen.room.location))
    )

    if distance is None or distance > GRACE_DISTANCE:
        raise HTTPException(
            status_code=400,
            detail="User is too far from the room",
        )

    db.add(
        Attendance(
            user_id=user_id,
            timetable_id=chosen.id,
            checked_in_date=today,
        )
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

    return chosen.id

@router.post("/{timetable_id}", status_code=201, description="Professor use only.")
async def mark_attendance_manually(
        timetable_id: int,
        user_id: int,
        professor: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
        select(Timetable).where(
            Timetable.id == timetable_id,
            Timetable.professor_id == professor.id,
        )
    )

    timetable = result.scalar_one_or_none()

    if timetable is None:
        raise HTTPException(
            status_code=403,
            detail="You do not own this timetable",
        )

    result = await db.execute(
        select(Registered).where(
            Registered.user_id == user_id,
            Registered.timetable_id == timetable_id,
        )
    )

    registration = result.scalar_one_or_none()

    if registration is None:
        raise HTTPException(
            status_code=404,
            detail="User is not registered for this timetable",
        )

    now = datetime.utcnow()
    today = now.date()

    db.add(
        Attendance(
            user_id=user_id,
            timetable_id=timetable_id,
            checked_in_date=today,
        )
    )
    await db.commit()


@router.websocket("/ws/check-in")
async def attendance_websocket(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws),
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()

    tracker = ByteTrackTracker()

    user_iom_embedding = np.asarray(
        user.iom_embedding,
        dtype=np.uint8,
    )

    key = derive_user_key(user.id)
    projection = generate_iom_projection(key)

    processor = CheckInProcessor(
        websocket.app.state,
        user_iom_embedding,
        projection,
    )
    processor.start()

    # Get location from start.
    location = await websocket.receive_json()
    latitude = location["latitude"]
    longitude = location["longitude"]

    try:
        while True:
            data = await websocket.receive_bytes()

            frame = cv2.imdecode(
                np.frombuffer(data, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )

            if frame is None:
                await websocket.send_json({"error": "could not decode frame"})
                continue

            bboxes, kpss = websocket.app.state.detector.detect(
                frame,
                max_num=0,
                metric="default",
            )

            tracks = []

            if len(bboxes) > 0:
                tracked = tracker.update(
                    sv.Detections(
                        xyxy=bboxes[:, :4],
                        confidence=bboxes[:, 4],
                    )
                )

                for box, track_id in zip(tracked.xyxy, tracked.tracker_id):
                    track_id = int(track_id)

                    if track_id < 0:
                        continue

                    kps = match_kps(box, bboxes, kpss)

                    tracks.append({
                        "track_id": track_id,
                        "bbox": box.tolist(),
                        "similarity": processor.track_sims.get(track_id),
                        "streak": processor.track_streaks.get(track_id, 0),
                        "spoof": processor.track_spoof.get(track_id, False),
                    })

                    processor.submit(data, box, kps, track_id)

            focus_track_id = None
            focus_streak = 0
            for t in tracks:
                if t["streak"] > focus_streak:
                    focus_streak = t["streak"]
                    focus_track_id = t["track_id"]

            await websocket.send_json({
                "tracks": tracks,
                "focus": (
                    {"track_id": focus_track_id, "streak": focus_streak}
                    if focus_track_id is not None
                    else None
                ),
                "attempts_remaining": processor.attempts_remaining,
            })

            if processor.spoof_blocked:
                await websocket.close(
                    code=1008,
                    reason="too many spoof attempts",
                )
                return

            if processor.confirm_track_id is not None:
                timetable_id = await record_attendance(
                    db,
                    user.id,
                    latitude,
                    longitude,
                )
                await websocket.send_json({
                    "confirmed": {
                        "track_id": processor.confirm_track_id,
                        "similarity": processor.confirm_similarity,
                        "timetable_id": timetable_id,
                    },
                })
                await websocket.close(
                    code=1000,
                    reason=(
                        f"confirmed track_id={processor.confirm_track_id} "
                        f"sim={processor.confirm_similarity:.2f}"
                    ),
                )
                return

    except WebSocketDisconnect:
        pass
    finally:
        await processor.stop()
