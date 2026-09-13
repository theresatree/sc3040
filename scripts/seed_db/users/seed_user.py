import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from tqdm import tqdm

from app.auth.embeddings import derive_user_key, generate_iom_projection, iom_hash
from app.auth.password import hash_password
from app.db.models import User, UserRole
from app.ml.operations import get_face_embedding
from app.ml.state import load_models

from . import SEED_NAMES

IMAGE_PATH = Path(__file__).resolve().parents[1] / "images"
MODEL_PATH = Path(__file__).resolve().parents[3] / "ml_models"
OUR_FACES = {
    "edmund.jpg": "Edmund",
    "yaosheng.jpg": "Yao Sheng",
    "hoeping.jpg": "Hoe Ping",
    "jack.jpg": "Jack",
    "weijie.jpg": "Wei Jie",
}
FACE_SEED_PATH = "face_"


def build_user(
    name: str,
    role: UserRole,
    image_bytes: bytes | None = None,
    state=None,
    gender: str = "male",
) -> tuple[User, np.ndarray | None]:
    face_embedding = None

    if state is not None:
        if image_bytes is None:
            raise ValueError("image_bytes is required when state is provided")

        face_embedding = np.asarray(
            get_face_embedding(
                image_bytes,
                state.detector,
                state.landmark,
                state.recognizer,
            ),
            dtype=np.float32,
        )

    email_slug = name.lower().replace(" ", ".")

    user = User(
        name=name,
        role=role,
        gender=gender,
        email=f"{email_slug}@test.com",
        password_hash=hash_password("password"),
    )

    return user, face_embedding


async def seed(
    db,
    staff_count: int = 5,
    student_count: int = 95,
    state=None,
    embed_faces: bool = True,
):
    rng = random.Random(0)

    if embed_faces and state is None:
        state = load_models(str(MODEL_PATH), cpu=True)

    def read_image(filename: str) -> bytes | None:
        if not embed_faces:
            return None
        return (IMAGE_PATH / filename).read_bytes()

    users = []

    # 5 named faces -> students
    for image, name in tqdm(OUR_FACES.items(), desc="Processing faces"):
        users.append(
            build_user(
                name,
                UserRole.STUDENT,
                read_image(image),
                state,
                "male",
            )
        )

    print("Our faces done")

    # First `staff_count` numbered faces -> staff
    for i in tqdm(range(staff_count), desc="Creating staffs"):
        name = SEED_NAMES[i]
        users.append(
            build_user(
                name,
                UserRole.STAFF,
                read_image(f"{FACE_SEED_PATH}{i:03d}.jpg"),
                state,
                rng.choice(["male", "female"]),
            )
        )

    print("Staffs done")

    # Remaining numbered faces -> students
    for i in tqdm(
        range(
            staff_count,
            staff_count + student_count,
        ),
        desc="Creating remaining students",
    ):
        name = SEED_NAMES[i]
        users.append(
            build_user(
                name,
                UserRole.STUDENT,
                read_image(f"{FACE_SEED_PATH}{i:03d}.jpg"),
                state,
                rng.choice(["male", "female"]),
            )
        )

    print("Remaining students done")

    user_objects = [user for user, _ in users]

    db.add_all(user_objects)
    await db.flush()

    # Generate IoM templates
    if embed_faces:
        for user, face_embedding in users:
            if user.name in OUR_FACES.values():
                continue

            key = derive_user_key(user.id)

            projection = generate_iom_projection(key)

            user.iom_embedding = iom_hash(
                face_embedding,
                projection,
            ).tolist()

            user.last_image_update = datetime.now(UTC)

    await db.commit()

    return user_objects
