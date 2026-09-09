from app.db.models import Registered
from app.db.database import SessionLocal  
import random
from tqdm import tqdm

async def seed(timetables, students):
    async with SessionLocal() as db:
        registered = []
        # Group timetable slots by subject
        subjects = {}

        for timetable in timetables:
            subjects.setdefault(timetable.subject, []).append(timetable)

        for student in tqdm(students, desc="Registering student"):
            # Register each student for every subject
            for subject_timetables in subjects.values():
                # Register for every timetable slot of that subject

                register_timtable = random.random() < 0.8 # 80% to register

                if register_timtable:
                    for timetable in subject_timetables:
                        registered.append(
                                Registered(
                                    user_id=student.id,
                                    timetable_id=timetable.id,
                                    )
                                )
    db.add_all(registered)
    await db.commit()
