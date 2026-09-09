import random
from datetime import time
from app.db.database import SessionLocal

from app.db.models import Timetable, DayOfWeek
from tqdm import tqdm

WEEKDAYS = [
    DayOfWeek.MONDAY,
    DayOfWeek.TUESDAY,
    DayOfWeek.WEDNESDAY,
    DayOfWeek.THURSDAY,
    DayOfWeek.FRIDAY,
]

SUBJECTS = [
    "SC3040",
    "SC3000",
    "SC2002",
    "SC2006",
    "SC2207",
    "SC3002",
    "SC4001",
    "SC4020",
]

# Realistic university class slots
TIME_SLOTS = [
    (time(8, 30), time(10, 20)),
    (time(10, 30), time(12, 20)),
    (time(12, 30), time(14, 20)),
    (time(14, 30), time(16, 20)),
]


def overlaps(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


def has_collision(
    professor_id,
    room_id,
    day,
    start,
    end,
    timetables,
):
    for timetable in timetables:
        if timetable.day_of_week != day:
            continue

        # Professor already teaching during this time
        if timetable.professor_id == professor_id:
            if overlaps(start, end, timetable.start, timetable.end):
                return True

        # Room already occupied during this time
        if timetable.room_id == room_id:
            if overlaps(start, end, timetable.start, timetable.end):
                return True

    return False


async def seed(professors, rooms):
    async with SessionLocal() as db:
        timetables = []

        print("Subjects")
        for i, subject in enumerate(SUBJECTS, 1):
            print(f"{i}. {subject}")

        for subject in tqdm(SUBJECTS, desc="Allocating timetables"):
            # A professor can teach multiple subjects
            professor = random.choice(professors)

            # Keep trying random combinations until there is no collision
            while True:
                day = random.choice(WEEKDAYS)
                room = random.choice(rooms)
                start, end = random.choice(TIME_SLOTS)

                if not has_collision(
                    professor.id,
                    room.id,
                    day,
                    start,
                    end,
                    timetables,
                ):
                    break

            timetables.append(
                Timetable(
                    subject=subject,
                    start=start,
                    end=end,
                    day_of_week=day,
                    professor_id=professor.id,
                    room_id=room.id,
                )
            )
    db.add_all(timetables)
    await db.commit()

    return timetables
