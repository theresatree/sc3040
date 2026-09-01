from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import UploadFile, HTTPException

from app.ml.operations import _crop_face


UPLOAD_DIR = Path("uploads/users")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        }


def save_face_image_crop(image_bytes: bytes, detector, size: int = 256) -> str:
    """
    We save it as 128x128, with 0.5x face size for padding around the face.
    """
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(
                status_code=400,
                detail="Invalid image",
                )

    bboxes, _ = detector.detect(img)
    if len(bboxes) == 0:
        raise HTTPException(
                status_code=400,
                detail="No face detected",
                )
    if len(bboxes) > 1:
        raise HTTPException(
                status_code=400,
                detail="Multiple faces detected",
                )

    x1, y1, x2, y2 = bboxes[0][:4].astype(int)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    crop = _crop_face(img_rgb, (x1, y1, x2, y2), expansion=1.5)
    crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_LANCZOS4)

    filename = f"{uuid4()}.jpg"
    path = UPLOAD_DIR / filename

    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    if not ok:
        raise HTTPException(
                status_code=500,
                detail="Could not encode image",
                )
    path.write_bytes(buf.tobytes())

    return str(path)

def delete_image(image_path: str) -> None:
    path = Path(image_path)

    try:
        path.unlink()
    except FileNotFoundError:
        pass
