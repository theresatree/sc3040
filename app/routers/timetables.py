from app.db.models import Registered
from app.schemas.timetable import UpdateMyTimetableRequest
from sqlalchemy.orm import selectinload
from app.db.enums import DayOfWeek
from sqlalchemy.exc import IntegrityError
from app.db.models import Timetable, User
from app.schemas.timetable import TimetableRequest, TimetableResponse, MyTimetableResponse
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import require_admin
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import select, or_, func

router = APIRouter(
    prefix="/timetables",
    tags=["Timetable slots"],
)

# TODO: Timetable return capacity + registered.

@router.get("/", status_code=200, response_model=list[TimetableResponse], description="Get all timetable created by professors, query is non-case sensitive and partial matching")
async def get_all_timetable(
        day_of_week : DayOfWeek | None = None,
        room_id : str | None = None,
        professor_name : str | None = None,
        subject: str | None = None,
        db: AsyncSession = Depends(get_db)
        ):

    query = (
        select(
            Timetable,
            func.count(Registered.user_id).label("registered_count"),
        )
        .outerjoin(
            Registered,
            Registered.timetable_id == Timetable.id,
        )
        .options(
            selectinload(Timetable.professor),
            selectinload(Timetable.room),
        )
        .group_by(Timetable.id)
    )

    if day_of_week is not None:
        query = query.where(Timetable.day_of_week == day_of_week)

    if room_id is not None:
        query = query.where(Timetable.room_id.ilike(f"%{room_id}"))

    if professor_name is not None:
        query = query.join(Timetable.professor).where(
            User.name.ilike(f"%{professor_name}%")
        )

    if subject is not None:
        query = query.where(
            Timetable.subject.ilike(f"%{subject}%")
        )

    result = await db.execute(query)
    rows = result.all()

    return [
        TimetableResponse(
            id=timetable.id,
            subject=timetable.subject,
            start=timetable.start,
            end=timetable.end,
            day_of_week=timetable.day_of_week,
            professor=timetable.professor,
            room=timetable.room,
            registered_count=registered_count,
            )
        for timetable, registered_count in rows
        ]

@router.get("/me", status_code=200, response_model=list[MyTimetableResponse], description="Professor only use. Get timetable created by myself")
async def get_my_timetable(
        user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
        select(
            Timetable,
            func.count(Registered.user_id).label("registered_count"),
        )
        .outerjoin(
            Registered,
            Registered.timetable_id == Timetable.id,
        )
        .where(
            Timetable.professor_id == user.id
        )
        .options(
            selectinload(Timetable.room),
        )
        .group_by(Timetable.id)
    )

    rows = result.all()

    return [
        MyTimetableResponse(
            id=timetable.id,
            subject=timetable.subject,
            start=timetable.start,
            end=timetable.end,
            day_of_week=timetable.day_of_week,
            room=timetable.room,
            registered_count=registered_count,
        )
        for timetable, registered_count in rows
    ]

@router.get("/subjects", status_code=200, response_model=list[str], description="Get all collated subjects available")
async def get_all_subjects(
        db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Timetable.subject)
        .distinct()
        .order_by(Timetable.subject)
    )

    return result.scalars().all()


@router.get("/{id}", status_code=200, response_model=TimetableResponse, description="Get timetable based on ID")
async def get_timetable_by_id(
        id: int,
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
        select(
            Timetable,
            func.count(Registered.user_id).label("registered_count"),
        )
        .outerjoin(
            Registered,
            Registered.timetable_id == Timetable.id,
        )
        .where(Timetable.id == id)
        .options(
            selectinload(Timetable.professor),
            selectinload(Timetable.room),
        )
        .group_by(Timetable.id)
    )

    row = result.one_or_none()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Timetable not found",
        )

    timetable, registered_count = row

    return TimetableResponse(
        id=timetable.id,
        subject=timetable.subject,
        start=timetable.start,
        end=timetable.end,
        day_of_week=timetable.day_of_week,
        professor=timetable.professor,
        room=timetable.room,
        registered_count=registered_count,
    )




@router.post("/", status_code=201, description="Professor use only. Create new timetable slot based on available room and time.")
async def create_new_timetable(
        data: TimetableRequest,
        user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    new_timetable = Timetable(
            subject = data.subject,
            start = data.start,
            end = data.end,
            day_of_week = data.day_of_week,
            professor_id = user.id,
            room_id = data.room_id
            )

    result = await db.execute(
            select(Timetable).where(
                Timetable.day_of_week == data.day_of_week,
                Timetable.start < data.end,
                Timetable.end > data.start,
                or_(
                    Timetable.room_id == data.room_id,
                    Timetable.professor_id == user.id,
                    ),
                )
            )

    collision = result.scalar_one_or_none()

    if collision:
        raise HTTPException(
            status_code=409,
            detail="Room or professor is already booked during this time",
        )

    try:
        db.add(new_timetable)
        await db.commit()
        await db.refresh(new_timetable)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=404,
                detail="Room or professor not found"
                )


@router.delete("/{id}", status_code=204, description="Professor use only. Delete OWN timetable slot based on ID")
async def delete_timetable_by_id(
        id: int,
        user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Timetable)
            .where(Timetable.professor_id == user.id)
            .where(Timetable.id == id)
            )
    
    delete = result.scalar_one_or_none()

    if not delete:
        raise HTTPException(
                status_code=404,
                detail="Timetable not found"
                )

    await db.delete(delete)
    await db.commit()

@router.patch("/{id}", status_code=200, description="Professor use only. Update OWN timetable slot based on ID. Cannot update if there's students registered")
async def update_timetable_by_id(
        id: int,
        data: UpdateMyTimetableRequest,
        user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Timetable).where(
                Timetable.id == id,
                Timetable.professor_id == user.id,
                )
            )

    timetable = result.scalar_one_or_none()

    if timetable is None:
        raise HTTPException(
                status_code=404,
                detail="Timetable not found",
                )

    # Cannot update if any students are registered
    registration = await db.scalar(
            select(Registered).where(
                Registered.timetable_id == id
                )
            )

    if registration is not None:
        raise HTTPException(
                status_code=409,
                detail="Cannot update timetable with existing registrations",
                )

    # We need check for collision first.
    new_room = data.room_id if data.room_id is not None else timetable.room_id
    new_day = data.day_of_week if data.day_of_week is not None else timetable.day_of_week
    new_start = data.start if data.start is not None else timetable.start
    new_end = data.end if data.end is not None else timetable.end

    if new_start >= new_end:
        raise HTTPException(
            status_code=400,
            detail="Start time must be before end time",
        )

    result = await db.execute(
        select(Timetable).where(
            Timetable.room_id == new_room,
            Timetable.day_of_week == new_day,
            Timetable.start < new_end,
            Timetable.end > new_start,
            Timetable.id != id,
        )
    )

    collision = result.scalar_one_or_none()

    if collision:
        raise HTTPException(
            status_code=409,
            detail="Room is already booked during this time",
        )


    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(timetable, field, value)

    await db.commit()
    await db.refresh(timetable)
