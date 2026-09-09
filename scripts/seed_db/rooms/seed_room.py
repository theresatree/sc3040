from app.db.database import SessionLocal
from app.db.models import Room
from geoalchemy2.elements import WKTElement


def make_point(latitude: float, longitude: float):
    return WKTElement(
        f"POINT({longitude} {latitude})",
        srid=4326,
    )


rooms = [
    Room(
        id="LT5",
        name="Lecture Theatre 5",
        location=make_point(
            1.3465893396633715,
            103.68063835904418,
        ),
        capacity=50,
    ),
    Room(
        id="LT2A",
        name="Lecture Theater 2A",
        location=make_point(
            1.3466145025215208,
            103.68136894946757,
        ),
        capacity=30,
    ),
    Room(
        id="LT3",
        name="Lecture Theatre 3",
        location=make_point(
            1.3460098589951248,
            103.68111354562252,
        ),
        capacity=240,
    ),
    Room(
        id="LT7",
        name="Lecture Theatre 7",
        location=make_point(
            1.34572083578564,
            103.68064885251582,
        ),
        capacity=240,
    ),
]


async def seed():
    async with SessionLocal() as db:
        print("Rooms")

        for i, room in enumerate(rooms, 1):
            print(
                f"{i}. {room.id} | {room.name} | "
                f"{room.capacity} seats | {room.location}"
            )

        db.add_all(rooms)
        await db.commit()

    return rooms
