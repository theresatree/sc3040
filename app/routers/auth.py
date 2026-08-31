from app.image import save_image
from sqlalchemy.exc import IntegrityError
from app.auth.password import hash_password
from app.schemas.auth import RegisterRequest
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import LoginRequest
from app.auth.jwt import create_access_token
from app.auth.password import verify_password
from app.db.database import get_db
from app.db.models import User

from app.dependencies import process_face_image

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
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

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

@router.post("/register", status_code=201)
async def register(
        request: Request,
        data : RegisterRequest = Depends(),
        db: AsyncSession = Depends(get_db),
        ):
    # We need Depends for our RegisterRequest because we're asking FastAPI
    # to look at the individual params rather than the whole thing as a JSON
    image_bytes = await data.image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Image is required",
        )

    embeddings = process_face_image(request.app.state, image_bytes)

    content_type = data.image.content_type
    if content_type is None:
        raise HTTPException(
            status_code=400,
            detail="Image content type is required",
        )

    image_url = save_image(image_bytes, content_type)

    user = User(
            name=data.name, 
            role=data.role, # If not specified, default to student
            gender=data.gender,
            email=data.email,
            password_hash=hash_password(data.password),
            face_embedding=embeddings,
            image_url=image_url
            )
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=409,
                detail="Email already registered",
                )

    return {"message": "User registered successfully"}
