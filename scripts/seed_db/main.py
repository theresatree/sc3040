from app.db.enums import UserRole
from app.db.models import User
from scripts.seed_db.register import seed_register
from scripts.seed_db.timetable import seed_timetable
from .users import seed_user
from .rooms import seed_room
import asyncio
from app.db.database import SessionLocal
from sqlalchemy import select

import onnxruntime
# Silence onnxruntime's per-inference dynamic-shape noise (e.g. det_10g's
# VerifyOutputSizes). Severity 3 = errors only; must be set before sessions.
onnxruntime.set_default_logger_severity(3)


async def get_users():
    async with SessionLocal() as db:
        professors = await db.execute(
                select(User)
                .where(User.role == UserRole.PROFESSOR)
                )
        students = await db.execute(
                select(User)
                .where(User.role == UserRole.STUDENT)
                )

    return professors.scalars().all(), students.scalars().all()

if __name__ == "__main__":
    # Note: Max pictures only 100
    asyncio.run(seed_user.seed(professor_count=5,student_count=45))
    print("Users inserted into database")

    rooms = asyncio.run(seed_room.seed())
    print("Rooms inserted into database")

    professors, students = asyncio.run(get_users())
    
    # Seed timetables
    timetables = asyncio.run(seed_timetable.seed(professors,rooms))
    print("Timetables inserted into database")

    # Register all students
    asyncio.run(seed_register.seed(timetables,students))
    print("Students registration inserted into database")
