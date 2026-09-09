from fastapi import HTTPException, APIRouter, Depends


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.dependencies import get_current_user, require_admin
from app.schemas.user import UserDataResponse
from app.db.models import User
from app.db.database import get_db

router = APIRouter(
        prefix="/users",
        tags=["users"],
        )


@router.get("/me", response_model=UserDataResponse, status_code=200)
async def get_me(
        user: User = Depends(get_current_user),
        ):
    return user

# ADMIN/STAFF ONLY
@router.get("/{id}", response_model=UserDataResponse, status_code=200, dependencies=[Depends(require_admin)])
async def get_user_by_id(
        user_id: int,
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(User).where(User.id==user_id)
            )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
                status_code=404,
                detail="User not found"
                )

    return user
