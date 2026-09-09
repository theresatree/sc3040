from pathlib import Path
import random
from tqdm import tqdm

from app.ml.state import load_models
from app.ml.operations import get_face_embedding
from app.auth.password import hash_password
from app.db.database import SessionLocal
from app.db.models import User, UserRole
from . import SEED_NAMES
import numpy as np

from app.auth.embeddings import derive_user_key, generate_iom_projection, iom_hash

IMAGE_PATH = Path(__file__).resolve().parents[1] / "images"
OUR_FACES = { "edmund.jpg": "Edmund",
             "yaosheng.jpg": "Yao Sheng",
             "hoeping.jpg": "Hoe Ping",
             "jack.jpg": "Jack",
             "weijie.jpg": "Wei Jie",
             }
FACE_SEED_PATH = "face_"


def build_user(name: str, role: UserRole, image_bytes: bytes, state, gender: str | None = None) -> tuple[User, np.ndarray]:

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
        gender=gender if gender else random.choice(["male", "female"]),
        email=f"{email_slug}@test.com",
        password_hash=hash_password("password"),
        iom_embedding=[0.0] * 128,
    )

    return user, face_embedding

async def seed(professor_count=5, student_count=95):
    model_dir = Path("/app/ml_models")
    state = load_models(str(model_dir), cpu=True)

    async with SessionLocal() as db:
        users = []

        # 5 named faces -> students
        for image, name in tqdm( OUR_FACES.items(), desc="Processing faces"):
            image_bytes = (Path(IMAGE_PATH) / image).read_bytes()

            users.append(build_user(name, UserRole.STUDENT, image_bytes, state, "male"))

        print("Our faces done")

        # First 5 numbered faces -> professors
        for i in tqdm( range(professor_count), desc="Creating professors"):
            name = SEED_NAMES[i]
            filename = f"{FACE_SEED_PATH}{i:03d}.jpg"
            image_bytes = (Path(IMAGE_PATH) / filename).read_bytes()

            users.append(build_user(name, UserRole.PROFESSOR, image_bytes, state))

        print("Professors done")

        # Remaining numbered faces -> students
        for i in tqdm( range( professor_count, professor_count + student_count,), desc="Creating remaining students"):
            name = SEED_NAMES[i]
            filename = f"{FACE_SEED_PATH}{i:03d}.jpg"
            image_bytes = (Path(IMAGE_PATH) / filename).read_bytes()

            users.append(build_user(name, UserRole.STUDENT, image_bytes, state))

        print("Remaining students done")

        # Extract just the User objects for SQLAlchemy
        user_objects = [user for user, _ in users]

        db.add_all(user_objects)
        await db.flush()

        # Generate IoM templates
        for user, face_embedding in users:
            key = derive_user_key(user.id)

            projection = generate_iom_projection(key)

            user.iom_embedding = iom_hash(
                face_embedding,
                projection,
            ).tolist()

        await db.commit()

    return user_objects
