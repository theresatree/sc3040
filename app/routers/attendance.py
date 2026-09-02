from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from app.db.database import get_db
from app.auth.dependencies import get_current_user_id
from app.dependencies import process_face_image
from app.db.models import User



router = APIRouter(
    prefix="/attendance",
    tags=["attendance"],
)


@router.post("/check-in", status_code=201)
async def check_in(
        request: Request,
        user_id: int = Depends(get_current_user_id),
        image: UploadFile = Form(...),
        db: AsyncSession = Depends(get_db),
        ):

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Image is required",
        )

    embeddings = process_face_image(request.app.state, image_bytes)

    # Check based on DB

    result = await db.execute(
        select(User.face_embedding).where(User.id == user_id)
    )

    user_embedding = result.scalar_one_or_none()

    if user_embedding is None:
        raise HTTPException(
            status_code=404,
            detail="User has no registered face",
        )

    similarity = float(
        request.app.state.recognizer.compute_sim(
            np.array(user_embedding),
            np.array(embeddings),
        )
    )

    if similarity < 0.5:
        raise HTTPException(
            status_code=401,
            detail="Face does not match",
        )

    return {"message": "Check-in successful", "similarity": similarity}
