from app.image import delete_image,save_face_image_crop 
from fastapi.responses import FileResponse
from fastapi import Request
from app.dependencies import process_face_image
from app.schemas.user import UserImageUpdateRquest
from sqlalchemy.exc import IntegrityError
from app.auth.password import hash_password, verify_password
from app.schemas.user import UserPasswordUpdateRequest
from fastapi import HTTPException, APIRouter, Depends, Form
from typing import Annotated


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
        user: Annotated[User, Depends(get_current_user)],
        ):
    return user

@router.get("/me/image", status_code=200)
async def get_my_image(
        user: Annotated[User, Depends(get_current_user)],
        ):
    return FileResponse(user.image_url)

# Users update their own password and/or face.
@router.patch("/me/password", status_code=204)
async def update_password(
        user: Annotated[User, Depends(get_current_user)],
        data: Annotated[UserPasswordUpdateRequest, Form()],
        db: Annotated[AsyncSession, Depends(get_db)]
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

@router.patch("/me/image", status_code=204)
async def update_image(
        request: Request,
        user: Annotated[User, Depends(get_current_user)],
        data: Annotated[UserImageUpdateRquest, Form()],
        db: Annotated[AsyncSession, Depends(get_db)]
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

# ADMIN/STAFF ONLY
@router.get("/{id}", response_model=UserDataResponse, status_code=200, dependencies=[Depends(require_admin)])
async def get_user_by_id(
        user_id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
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

# ADMIN/STAFF ONLY
@router.get("/{id}/image", status_code=200, dependencies=[Depends(require_admin)])
async def get_user_image_by_id(
        user_id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
        ):
    result = await db.execute(
            select(User.image_url).where(User.id == user_id)
            )

    image_url = result.scalar_one_or_none()

    if not image_url:
        raise HTTPException(
                status_code=404,
                detail="Image not found",
                )

    return FileResponse(image_url)

# ADMIN/STAFF ONLY
@router.delete("/{id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_user_by_id(
        user_id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
        ):

    result = await db.execute(
            select(User).where(User.id == user_id)
            )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
                status_code=404,
                detail="User not found"
                )

    await db.delete(user)
    await db.commit()
