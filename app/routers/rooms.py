from app.auth.dependencies import require_admin
from app.db.database import get_db

from fastapi import HTTPException, Depends, APIRouter
from app.schemas.room import CreateRoomRequest, RoomDataResponse, UpdateRoomRequest

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Room

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
)

# All GET should be non-admin i think?
@router.get("/", status_code=200, response_model=list[RoomDataResponse])
async def get_all_rooms(
        db : AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Room)
            )

    rooms = result.scalars().all()

    if not rooms:
        raise HTTPException(
                status_code=404,
                detail="No rooms found"
                )

    return rooms

@router.get("/{room_id}", status_code=200, response_model=RoomDataResponse)
async def get_room_by_id(
        room_id: str,
        db : AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Room).where(Room.id == room_id)
            )

    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(
                status_code=404,
                detail="Room not found"
                )

    return room


@router.post("/", status_code=201, response_model=RoomDataResponse,dependencies=[Depends(require_admin)])
async def create_new_room(
        data: CreateRoomRequest,
        db: AsyncSession = Depends(get_db)
        ):

    # Check room_id against database first.
    room = Room(
            id = data.id,
            name = data.name,
            longitude = data.longitude,
            latitude = data.latitude,
            capacity = data.capacity
            )

    db.add(room)
    try:
        await db.commit()
        await db.refresh(room)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=409,
                detail="Room ID already exists"
                )
    return room

@router.delete("/{room_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_room_by_id(
        room_id: str,
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Room).where(Room.id == room_id)
            )

    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(
                status_code=404,
                detail="Room not found"
                )

    await db.delete(room)
    await db.commit()

@router.patch("/{room_id}", status_code=200, response_model=RoomDataResponse, dependencies=[Depends(require_admin)])
async def update_room_by_id(
        room_id: str,
        data: UpdateRoomRequest,
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(Room).where(Room.id==room_id)
            )

    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(
                status_code=404,
                detail="Room not found"
                )

    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(room, field, value)

    try:
        await db.commit()
        await db.refresh(room)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Room ID already exists",
        )

    return room
