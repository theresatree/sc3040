from fastapi import HTTPException

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
