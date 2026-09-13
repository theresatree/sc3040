from datetime import UTC, datetime

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.embeddings import derive_user_key, generate_iom_projection, iom_hash
from app.constants import LAST_IMAGE_UPDATE_GRACE_PERIOD
from app.db.database import get_db
from app.db.models import User
from app.ml.operations import get_face_embedding
from app.schemas.user import UserDataResponse

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/me", response_model=UserDataResponse, status_code=200)
async def get_me(
    user: User = Depends(get_current_user),
):
    return UserDataResponse(
        name=user.name,
        role=user.role,
        gender=user.gender,
        email=user.email,
        has_image=user.iom_embedding is not None,
    )


@router.post("/me/image", status_code=201)
async def update_image(
    request: Request,
    user: User = Depends(get_current_user),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):

    now = datetime.now(UTC)

    if (
        user.last_image_update
        and now < user.last_image_update + LAST_IMAGE_UPDATE_GRACE_PERIOD
    ):
        raise HTTPException(
            status_code=400,
            detail="Image was updated too recently.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Image file is empty.",
        )

    face_embedding = np.asarray(
        get_face_embedding(
            image_bytes,
            request.app.state.detector,
            request.app.state.landmark,
            request.app.state.recognizer,
        ),
        dtype=np.float32,
    )

    key = derive_user_key(user.id)
    projection = generate_iom_projection(key)

    user.iom_embedding = iom_hash(face_embedding, projection).tolist()
    user.last_image_update = datetime.now(UTC)

    await db.commit()


# ADMIN/STAFF ONLY
@router.get(
    "/{user_id}",
    response_model=UserDataResponse,
    status_code=200,
    dependencies=[Depends(require_admin)],
)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserDataResponse(
        name=user.name,
        role=user.role,
        gender=user.gender,
        email=user.email,
        has_image=user.iom_embedding is not None,
    )
