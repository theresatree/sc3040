import asyncio

import onnxruntime

from app.db.database import SessionLocal
from app.db.enums import UserRole
from scripts.seed_db.register import seed_register
from scripts.seed_db.rooms import seed_room
from scripts.seed_db.timetable import seed_timetable
from scripts.seed_db.users import seed_user

# Silence onnxruntime's per-inference dynamic-shape noise (e.g. det_10g's
# VerifyOutputSizes). Severity 3 = errors only; must be set before sessions.
onnxruntime.set_default_logger_severity(3)


async def seed_all(staff_count: int = 5, student_count: int = 45):
    async with SessionLocal() as db:
        users = await seed_user.seed(
            db,
            staff_count=staff_count,
            student_count=student_count,
        )
        print("Users inserted into database")

        rooms = await seed_room.seed(db)
        print("Rooms inserted into database")

        staffs = [user for user in users if user.role == UserRole.STAFF]
        students = [user for user in users if user.role == UserRole.STUDENT]

        timetables = await seed_timetable.seed(db, staffs, rooms)
        print("Timetables inserted into database")

        await seed_register.seed(db, timetables, students)
        print("Students registration inserted into database")

        return users, rooms, timetables


if __name__ == "__main__":
    # Note: Max pictures only 100
    asyncio.run(seed_all())
