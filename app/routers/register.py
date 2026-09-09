from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.auth.dependencies import get_current_user_id
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import  APIRouter, Depends
from app.db.models import Registered
from app.schemas.register import RegistrationData
from app.db.database import get_db

router = APIRouter(
        prefix="/register",
        tags=["register"],
        )


@router.get("/me", response_model=list[RegistrationData], status_code=200, description="Get my own registered timetable")
async def get_my_registration(
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
        ):
    results = await db.execute(
            select(Registered)
            .options(
                selectinload(Registered.timetable)
                )
            .where(Registered.user_id == user_id)
            )

    return results.scalars().all()
