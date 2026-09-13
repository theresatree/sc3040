from datetime import UTC, date, datetime, time

from geoalchemy2 import Geography
from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .enums import DayOfWeek, UserGender, UserRole


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole, name="user_role"))
    gender: Mapped[UserGender] = mapped_column(SQLEnum(UserGender, name="user_gender"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    iom_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(128), nullable=True
    )
    last_image_update: Mapped[datetime | None] = mapped_column(
        default=None,
        nullable=True,
    )


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[object] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=False,
        )
    )
    capacity: Mapped[int]


class Timetable(Base):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(100))
    start: Mapped[time]
    end: Mapped[time]
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        SQLEnum(DayOfWeek, name="day_of_week")
    )
    staff_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="timetables_staff_id_fkey")
    )

    room_id: Mapped[str] = mapped_column(
        ForeignKey("rooms.id", name="timetables_room_id_fkey")
    )

    staff: Mapped["User"] = relationship()
    room: Mapped["Room"] = relationship()


class Registered(Base):
    __tablename__ = "registered"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="registered_user_id_fkey"),
        primary_key=True,
    )
    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id", name="registered_timetable_id_fkey"),
        primary_key=True,
    )
    timetable: Mapped["Timetable"] = relationship()


class Attendance(Base):
    __tablename__ = "attendance"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="attendance_user_id_fkey"),
        primary_key=True,
    )

    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id", name="attendance_timetable_id_fkey"),
        primary_key=True,
    )

    checked_in_date: Mapped[date] = mapped_column(
        primary_key=True,
    )

    checked_in_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
