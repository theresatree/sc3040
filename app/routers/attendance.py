import asyncio
from datetime import UTC, datetime, timedelta

import cv2
import numpy as np
import supervision as sv
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from trackers import ByteTrackTracker

from app.auth.dependencies import get_current_user_ws, require_admin
from app.auth.embeddings import derive_user_key, generate_iom_projection
from app.constants import FRAME_SKIP, GRACE_DISTANCE, GRACE_PERIOD
from app.db.database import get_db
from app.db.enums import DayOfWeek
from app.db.models import Attendance, Registered, Timetable, User
from app.ml.checkin import CheckInProcessor, match_detection

router = APIRouter(
    prefix="/attendance",
    tags=["attendance"],
)


def decode_and_detect(data: bytes, detector):
    frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return None, None, None
    bboxes, kpss = detector.detect(frame, max_num=0, metric="default")
    return frame, bboxes, kpss


async def record_attendance(
    db: AsyncSession, user_id: int, latitude: float, longitude: float
) -> int | None:
    now = datetime.now(UTC)
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
            if t.day_of_week == current_day and t.start <= current_time <= t.end
        ),
        None,
    )

    if chosen is None:
        raise HTTPException(
            status_code=404,
            detail="No class",
        )

    grace_end = (
        datetime.combine(today, chosen.start) + timedelta(minutes=GRACE_PERIOD)
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


@router.post("/{timetable_id}", status_code=201, description="Staff use only.")
async def mark_attendance_manually(
    timetable_id: int,
    user_id: int,
    staff: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Timetable).where(
            Timetable.id == timetable_id,
            Timetable.staff == staff.id,
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

    now = datetime.now(UTC)
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

    loop = asyncio.get_running_loop()

    # Get location from the client first.
    location = await websocket.receive_json()
    latitude = location["latitude"]
    longitude = location["longitude"]

    frame_count = 0
    last_tracks: list = []
    last_focus = None

    try:
        while True:
            data = await websocket.receive_bytes()
            frame_count += 1

            # Skip frames to reduce processing load.
            if frame_count % FRAME_SKIP != 0:
                await websocket.send_json(
                    {
                        "tracks": last_tracks,
                        "focus": last_focus,
                        "attempts_remaining": processor.attempts_remaining,
                    }
                )
                continue

            # ---------------------------------------------------------
            # Buffalo_L detection
            # ---------------------------------------------------------
            frame, bboxes, kpss = await loop.run_in_executor(
                processor.pool,
                decode_and_detect,
                data,
                websocket.app.state.detector,
            )

            if frame is None:
                await websocket.send_json(
                    {
                        "error": "could not decode frame",
                    }
                )
                continue

            tracks = []

            if len(bboxes) == 0:
                processor.note_visible_tracks(set())

                last_tracks = []
                last_focus = None

                await websocket.send_json(
                    {
                        "tracks": [],
                        "focus": None,
                        "attempts_remaining": processor.attempts_remaining,
                    }
                )

            else:
                # -----------------------------------------------------
                # ByteTrack
                #
                # ByteTrack is ONLY used to assign persistent IDs.
                # Its bounding box is NOT used for recognition/spoof.
                # -----------------------------------------------------
                tracked = tracker.update(
                    sv.Detections(
                        xyxy=bboxes[:, :4],
                        confidence=bboxes[:, 4],
                    )
                )

                visible_track_ids = set()
                candidate_for_submit = None
                candidate_area = -1

                locked_track_id = processor.locked_track_id

                for tracked_box, track_id in zip(
                    tracked.xyxy,
                    tracked.tracker_id,
                ):
                    track_id = int(track_id)

                    if track_id < 0:
                        continue

                    visible_track_ids.add(track_id)

                    # -------------------------------------------------
                    # Match the ByteTrack track back to the original
                    # Buffalo_L detection.
                    #
                    # From this point onward, use Buffalo's bbox/kps.
                    # -------------------------------------------------
                    buffalo_box, buffalo_kps = match_detection(
                        tracked_box,
                        bboxes,
                        kpss,
                    )

                    tracks.append(
                        {
                            "track_id": track_id,
                            "bbox": buffalo_box[:4].tolist(),
                            "similarity": processor.track_sims.get(track_id),
                            "streak": processor.track_streaks.get(
                                track_id,
                                0,
                            ),
                            "spoof": processor.track_spoof.get(
                                track_id,
                                False,
                            ),
                        }
                    )

                    # -------------------------------------------------
                    # If already locked, only submit that track.
                    # -------------------------------------------------
                    if locked_track_id is not None:
                        if track_id == locked_track_id:
                            processor.submit(
                                data,
                                buffalo_box,
                                buffalo_kps,
                                track_id,
                            )

                    # -------------------------------------------------
                    # If not locked, find the largest Buffalo face.
                    # -------------------------------------------------
                    else:
                        x1, y1, x2, y2 = buffalo_box[:4]
                        area = (x2 - x1) * (y2 - y1)

                        if area > candidate_area:
                            candidate_area = area
                            candidate_for_submit = (
                                buffalo_box,
                                buffalo_kps,
                                track_id,
                            )

                # -----------------------------------------------------
                # Submit the largest Buffalo face while unlocked.
                # -----------------------------------------------------
                if locked_track_id is None and candidate_for_submit is not None:
                    box, kps, track_id = candidate_for_submit

                    processor.submit(
                        data,
                        box,
                        kps,
                        track_id,
                    )

                # -----------------------------------------------------
                # Tell the processor which ByteTrack IDs are visible.
                # -----------------------------------------------------
                processor.note_visible_tracks(visible_track_ids)

                # -----------------------------------------------------
                # Determine focus track.
                # -----------------------------------------------------
                focus_track_id = None
                focus_streak = 0

                for track in tracks:
                    if track["streak"] > focus_streak:
                        focus_streak = track["streak"]
                        focus_track_id = track["track_id"]

                last_tracks = tracks

                last_focus = (
                    {
                        "track_id": focus_track_id,
                        "streak": focus_streak,
                    }
                    if focus_track_id is not None
                    else None
                )

                await websocket.send_json(
                    {
                        "tracks": last_tracks,
                        "focus": last_focus,
                        "attempts_remaining": processor.attempts_remaining,
                    }
                )

            # ---------------------------------------------------------
            # Spoof protection
            # ---------------------------------------------------------
            if processor.spoof_blocked:
                await websocket.close(
                    code=1008,
                    reason="too many spoof attempts",
                )
                return

            # ---------------------------------------------------------
            # Successful recognition
            # ---------------------------------------------------------
            if processor.confirm_track_id is not None:
                timetable_id = await record_attendance(
                    db,
                    user.id,
                    latitude,
                    longitude,
                )

                await websocket.send_json(
                    {
                        "confirmed": {
                            "track_id": processor.confirm_track_id,
                            "similarity": processor.confirm_similarity,
                            "timetable_id": timetable_id,
                        },
                    }
                )

                await websocket.close(
                    code=1000,
                    reason=(
                        f"confirmed "
                        f"track_id={processor.confirm_track_id} "
                        f"sim={processor.confirm_similarity:.2f}"
                    ),
                )
                return

    except WebSocketDisconnect:
        pass

    finally:
        await processor.stop()
