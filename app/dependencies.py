from fastapi import HTTPException
import base64

from app.ml.operations import get_face_embedding, check_spoofing


def process_face_image(state, image_bytes: bytes) -> list[float]:
    """Decode, detect, embed and anti-spoof a face image from a request.

    Raises HTTPException 400 if the image is invalid, has no (or multiple)
    faces, or is detected as a spoof.
    """
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Image is invalid",
        )

    embeddings = get_face_embedding(
        image_bytes,
        state.detector,
        state.landmark,
        state.recognizer,
    )

    if not check_spoofing(
        image_bytes,
        state.detector,
        state.spoofing,
    ):
        raise HTTPException(
            status_code=400,
            detail="Spoofing detected",
        )

    return embeddings

def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
