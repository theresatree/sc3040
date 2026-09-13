import hashlib

import numpy as np
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

SECRET_KEY = "8a21821f32711a2fbbeac60f5c52a31a8bbfb5132fb08a8bd59964ff5e347033"

EMBEDDING_DIM = 512
NUM_GROUPS = 128  # no of computations
GROUP_SIZE = 4


def derive_user_key(user_id: int) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=f"face-iom:{user_id}".encode(),
    ).derive(SECRET_KEY.encode())


def generate_iom_projection(key: bytes) -> np.ndarray:
    seed_bytes = hashlib.sha256(key).digest()
    seed = int.from_bytes(seed_bytes[:8], "little")

    rng = np.random.default_rng(seed)

    return rng.standard_normal((NUM_GROUPS, GROUP_SIZE, EMBEDDING_DIM)).astype(
        np.float32
    )


def iom_hash(embedding: np.ndarray, projection: np.ndarray) -> np.ndarray:
    embedding = np.asarray(embedding, dtype=np.float32)

    if embedding.shape != (EMBEDDING_DIM,):
        raise ValueError(f"Expected ({EMBEDDING_DIM},), got {embedding.shape}")

    scores = np.einsum(
        "gkd,d->gk",
        projection,
        embedding,
    )

    return np.argmax(scores, axis=1).astype(np.uint8)


def iom_similarity(template1: np.ndarray, template2: np.ndarray) -> float:

    return float(np.mean(template1 == template2))
