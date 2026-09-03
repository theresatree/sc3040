from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.db.models import User, Room
from sqlalchemy.orm import selectinload
from app.db.models import Registered
from app.db.models import Timetable
from app.auth.dependencies import require_student
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.schemas.registrations import MyRegistrationResponse


router = APIRouter(
    prefix="/register",
    tags=["Student's Registration"],
)


@router.get("/me", response_model=list[MyRegistrationResponse], status_code=200, description="Student use only. Get a list of all registered classes")
async def get_my_registrations(
        user: User = Depends(require_student),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
        select(Timetable)
        .join(
            Registered,
            Registered.timetable_id == Timetable.id
        )
        .where(
            Registered.user_id == user.id
        )
        .options(
            selectinload(Timetable.professor)
            )
    )

    timetables = result.scalars().all()

    return [
        MyRegistrationResponse(
            id=t.id,
            subject=t.subject,
            start=t.start,
            end=t.end,
            day_of_week=t.day_of_week,
            room_id=t.room_id,
            professor_name=t.professor.name,
        )
        for t in timetables
    ]

@router.post("/{timetable_id}", status_code=201, description="Student use only. Book a timetable slot")
async def book_a_timetable_slot_by_id(
        timetable_id: int,
        user: User = Depends(require_student),
        db : AsyncSession = Depends(get_db)
        ):

    # Get timetable + room
    result = await db.execute(
        select(Timetable, Room)
        .join(Room, Timetable.room_id == Room.id)
        .where(Timetable.id == timetable_id)
    )

    row = result.one_or_none()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Timetable not found",
        )

    timetable, room = row


    # Count students
    student_count = await db.scalar(
        select(func.count(Registered.user_id))
        .where(Registered.timetable_id == timetable_id)
    )

    if student_count >= room.capacity:
        raise HTTPException(
            status_code=409,
            detail="Room is full",
        )


    # Check collision registration
    student_collision = await db.scalar(
        select(Timetable)
        .join(
            Registered,
            Registered.timetable_id == Timetable.id
        )
        .where(
            Registered.user_id == user.id,
            Timetable.day_of_week == timetable.day_of_week,
            Timetable.start < timetable.end,
            Timetable.end > timetable.start,
        )
    )

    if student_collision is not None:
        raise HTTPException(
            status_code=409,
            detail="Timetable conflicts with an existing registration",
        )

    try:
        db.add(
            Registered(
                user_id=user.id,
                timetable_id=timetable_id,
            )
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Student is already registered for this timetable",
        )

@router.delete("/{timetable_id}", status_code=204, description="Student use only. Delete timetable registered by ID")
async def remove_registered_timetable_by_id(
        timetable_id: int,
        user: User = Depends(require_student),
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.scalar(
            select(Registered).
            where(
                Registered.user_id == user.id,
                Registered.timetable_id == timetable_id
                )
            )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Timetable is not registered by user",
        )

    await db.delete(result)
    await db.commit()
