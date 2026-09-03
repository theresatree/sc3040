from app.dependencies import image_to_base64
from app.db.enums import UserRole
from app.db.models import Registered
from app.image import delete_image,save_face_image_crop 
from app.dependencies import process_face_image
from app.schemas.user import UserImageUpdateRquest
from sqlalchemy.exc import IntegrityError
from app.auth.password import hash_password, verify_password
from app.schemas.user import UserPasswordUpdateRequest
from fastapi import HTTPException, APIRouter, Depends, Request


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.auth.dependencies import get_current_user, require_admin
from app.schemas.user import UserDataResponse
from app.db.models import User
from app.db.database import get_db

router = APIRouter(
        prefix="/users",
        tags=["User Operations"],
        )

# ADMIN/STAFF ONLY
@router.get("/", response_model=list[UserDataResponse], status_code=200, dependencies=[Depends(require_admin)], description="Professor only. Get all users")
async def get_all_users(
        role: UserRole | None = None,
        db: AsyncSession = Depends(get_db)
        ):

    query = select(User).where(User.is_active == True)

    if role is not None:
        query = query.where(User.role == role)

    result = await db.execute(query)
    users = result.scalars().all()

    return [
        UserDataResponse(
            name=user.name,
            role=user.role,
            gender=user.gender,
            email=user.email,
            image=f"data:image/jpeg;base64,{image_to_base64(user.image_url)}",
        )
        for user in users
    ]

@router.get("/me", response_model=UserDataResponse, status_code=200, description="Get current user's information")
async def get_me(
        user: User = Depends(get_current_user),
        ):
    
    return UserDataResponse(
            name=user.name,
            role=user.role,
            gender=user.gender,
            email=user.email,
            image=f"data:image/jpeg;base64,{image_to_base64(user.image_url)}",
        )

@router.patch("/me/password", status_code=204, description="Update current user's password")
async def update_password(
        user: User = Depends(get_current_user),
        data: UserPasswordUpdateRequest = Depends(),
        db: AsyncSession = Depends(get_db)
        ):

    password_match = verify_password(data.curr_password, user.password_hash)

    if not password_match:
        raise HTTPException(
                status_code=401,
                detail="Password mismatch"
                )

    new_password_hash = hash_password(data.password)
    user.password_hash = new_password_hash
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=409,
                detail="Password update failed",
                )

@router.patch("/me/image", status_code=204, description="Update current user's image")
async def update_image(
        request: Request,
        user: User = Depends(get_current_user),
        data: UserImageUpdateRquest = Depends(),
        db: AsyncSession = Depends(get_db)
        ):

    image_bytes = await data.image.read()

    if not image_bytes:
        raise HTTPException(
                status_code=400,
                detail="Image is required",
                )

    embeddings = process_face_image(request.app.state, image_bytes)

    image_url = save_face_image_crop(image_bytes, request.app.state.detector)
    old_image_url = user.image_url
    user.face_embedding = embeddings
    user.image_url=image_url

    try:
        await db.commit()
        await db.refresh(user)

        # DB update succeeded, now remove old image
        if old_image_url:
            delete_image(old_image_url)

    except IntegrityError:
        await db.rollback()

        # Also delete the newly saved image because DB update failed
        delete_image(image_url)

        raise HTTPException(
                status_code=409,
                detail="Image update failed",
                )



@router.get("/{id}", response_model=UserDataResponse, status_code=200, description="Get user based on ID")
async def get_user_by_id(
        id: int,
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(User).where(User.id==id)
            )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
                status_code=404,
                detail="User not found"
                )

    return UserDataResponse(
            name=user.name,
            role=user.role,
            gender=user.gender,
            email=user.email,
            image=f"data:image/jpeg;base64,{image_to_base64(user.image_url)}",
        ) 

# ADMIN/STAFF ONLY
@router.delete("/{id}", status_code=204, dependencies=[Depends(require_admin)], description="Professor only.Soft-delete STUDENTS based on ID, their current registration is deleted.")
async def deactivate_user_by_id(
        id: int,
        db: AsyncSession = Depends(get_db)
        ):

    result = await db.execute(
            select(User).where(User.id == id)
            )

    user = result.scalar_one_or_none()

    if not user.is_active:
        raise HTTPException(
                status_code=403,
                detail="User is inactive",
                )

    if user is None:
        raise HTTPException(
                status_code=404,
                detail="User not found"
                )

    if user.role != UserRole.STUDENT:
        raise HTTPException(
                status_code=403,
                detail="Only student can be deactivated."
                )

    await db.execute(
            delete(Registered).where(
                Registered.user_id == user.id
                )
            )

    user.is_active = False

    await db.commit()
