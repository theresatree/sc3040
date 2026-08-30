from fastapi import APIRouter
from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.db.models import User

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/")
async def get_users():
    return {"message": "users router works"}

@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
):
    return user
