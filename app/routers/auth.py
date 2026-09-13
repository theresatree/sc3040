from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.password import verify_password
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import LoginRequest

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/login")
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # Find user
    result = await db.execute(select(User).where(User.email == data.email))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # Check password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # Create JWT
    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
