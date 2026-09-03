from app.db.enums import UserRole
import jwt
from app.auth.jwt import decode_access_token

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User


bearer_scheme = HTTPBearer()


async def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        ) -> int:
    try:
        token = credentials.credentials

        payload = decode_access_token(token)

        return int(payload["sub"])

    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
                status_code=401,
                detail="Invalid token",
                )

async def get_current_user(
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
        ) -> User:
    result = await db.execute(
            select(User).where(User.id == user_id)
            )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
                status_code=401,
                detail="User not found",
                )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is deactivated",
        )

    return user

async def require_admin(
      user: User = Depends(get_current_user),
        ) -> User:

    if user.role == UserRole.STUDENT:
        raise HTTPException(
                status_code=403,
                detail="Student access denied",
                )
    return user

async def require_student(
        user: User = Depends(get_current_user)
        ) -> User:

    if user.role != UserRole.STUDENT:
        raise HTTPException(
                status_code=403,
                detail="Student access only",
                )
    return user

