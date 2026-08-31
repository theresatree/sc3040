from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, HTTPException


UPLOAD_DIR = Path("uploads/users")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        }


def save_image(image_bytes: bytes, content_type: str) -> str:
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
                status_code=400,
                detail="Unsupported image format",
                )

    if not image_bytes:
        raise HTTPException(
                status_code=400,
                detail="Image is empty",
                )

    extension = ALLOWED_TYPES[content_type]
    filename = f"{uuid4()}{extension}"

    path = UPLOAD_DIR / filename

    with path.open("wb") as f:
        f.write(image_bytes)

    return str(path)

def delete_image(image_path: str) -> None:
    path = Path(image_path)

    try:
        path.unlink()
    except FileNotFoundError:
        pass
