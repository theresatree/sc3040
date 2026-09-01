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

from sqlalchemy import select

router = APIRouter(
    prefix="/timetables",
    tags=["timetables"],
)

@router.get("/", status_code=200, response_model=list[TimetableResponse])
async def get_all_timetable(
        day_of_week : DayOfWeek | None = None,
        room_id : str | None = None,
        professor_id : int | None = None,
        subject: str | None = None,
        db: AsyncSession = Depends(get_db)
        ):

    query = select(Timetable).options(
        selectinload(Timetable.professor),
        selectinload(Timetable.room),
    )
    if day_of_week is not None:
        query = query.where(Timetable.day_of_week == day_of_week)
    if room_id is not None:
        query = query.where(Timetable.room_id == room_id)
    if professor_id is not None:
        query = query.where(Timetable.professor_id == professor_id)
    if subject is not None:
        query = query.where(Timetable.subject == subject)

    result = await db.execute(query)

    return result.scalars().all()


@router.get("/{timetable_id}", status_code=200, response_model=TimetableResponse)
async def get_timetable_by_id(
        timetable_id: int,
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Timetable)
            .where(Timetable.id == timetable_id)
            .options(selectinload(Timetable.professor), selectinload(Timetable.room))
            )

    timetable = result.scalar_one_or_none()

    if not timetable:
        raise HTTPException(
                status_code=404,
                detail="Timetable not found"
                )

    return timetable


@router.get("/subjects", status_code=200, response_model=list[str])
async def get_all_subjects(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Timetable.subject)
        .distinct()
        .order_by(Timetable.subject)
    )

    return result.scalars().all()

@router.get("/me", status_code=200, response_model=list[MyTimetableResponse])
async def get_my_timetable(
        user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Timetable).where(Timetable.professor_id == user.id).options(selectinload(Timetable.room))
            )

    return result.scalars().all()

@router.post("/", status_code=201)
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
                Timetable.room_id == data.room_id,
                Timetable.day_of_week == data.day_of_week,
                Timetable.start < data.end,
                Timetable.end > data.start,
                )
            )

    collision = result.scalar_one_or_none()

    if collision:
        raise HTTPException(
            status_code=409,
            detail="Room is already booked during this time",
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


@router.delete("/{timetable_id}", status_code=204)
async def delete_timetable_by_id(
        timetable_id: int,
        user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Timetable)
            .where(Timetable.professor_id == user.id)
            .where(Timetable.id == timetable_id)
            )
    
    delete = result.scalar_one_or_none()

    if not delete:
        raise HTTPException(
                status_code=404,
                detail="Timetable not found"
                )

    await db.delete(delete)
    await db.commit()

@router.patch("/{timetable_id}", status_code=200)
async def update_timetable_by_id(
        timetable_id: int,
        data: UpdateMyTimetableRequest,
        user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Timetable)
            .where(Timetable.id==timetable_id)
            .where(Timetable.professor_id==user.id)
            )

    timetable = result.scalar_one_or_none()

    if not timetable:
        raise HTTPException(
                status_code=404,
                detail="Timetable not found"
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
            Timetable.id != timetable_id,
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
