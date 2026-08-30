from app.auth.password import hash_password
from app.db.database import SessionLocal
from app.db.models import User, UserRole


def seed():
    with SessionLocal() as db:
        users = [
            User(
                name="Test Student",
                role=UserRole.STUDENT,
                gender="male",
                email="student@test.com",
                password_hash=hash_password("password123"),
            ),
            User(
                name="Test Staff",
                role=UserRole.STAFF,
                gender="female",
                email="staff@test.com",
                password_hash=hash_password("password123"),
            ),
            User(
                name="Test Admin",
                role=UserRole.ADMIN,
                gender="male",
                email="admin@test.com",
                password_hash=hash_password("password123"),
            ),
        ]

        db.add_all(users)
        db.commit()

if __name__ == "__main__":
    seed()
