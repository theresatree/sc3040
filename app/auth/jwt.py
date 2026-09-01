from datetime import datetime, timedelta, timezone

import jwt

SECRET_KEY = "83deffea5dafad4f9d57569768f169f622a5ace94f3cfaeb7e26216f815072ed" # Hardcode it, since no checks anyways.
ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )
