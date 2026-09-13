from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_admin
from app.db.database import get_db
from app.db.enums import DayOfWeek
from app.db.models import Timetable, User
from app.schemas.timetable import MyTimetableResponse, TimetableResponse

router = APIRouter(
    prefix="/timetables",
    tags=["timetables"],
)


@router.get("/", status_code=200, response_model=list[TimetableResponse])
async def get_all_timetable(
    day_of_week: DayOfWeek | None = None,
    room_id: str | None = None,
    staff_id: int | None = None,
    subject: str | None = None,
    db: AsyncSession = Depends(get_db),
):

    query = select(Timetable).options(
        selectinload(Timetable.staff),
        selectinload(Timetable.room),
    )
    if day_of_week is not None:
        query = query.where(Timetable.day_of_week == day_of_week)
    if room_id is not None:
        query = query.where(Timetable.room_id == room_id)
    if staff_id is not None:
        query = query.where(Timetable.staff_id == staff_id)
    if subject is not None:
        query = query.where(Timetable.subject == subject)

    result = await db.execute(query)

    return result.scalars().all()


@router.get("/me", status_code=200, response_model=list[MyTimetableResponse])
async def get_my_timetable(
    user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Timetable)
        .where(Timetable.staff_id == user.id)
        .options(selectinload(Timetable.room))
    )

    return result.scalars().all()


@router.get("/subjects", status_code=200, response_model=list[str])
async def get_all_subjects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Timetable.subject).distinct().order_by(Timetable.subject)
    )

    return result.scalars().all()


@router.get("/{timetable_id}", status_code=200, response_model=TimetableResponse)
async def get_timetable_by_id(timetable_id: int, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Timetable)
        .where(Timetable.id == timetable_id)
        .options(selectinload(Timetable.staff), selectinload(Timetable.room))
    )

    timetable = result.scalar_one_or_none()

    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    return timetable
