from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Enum as SQLEnum
from .enums import UserRole, UserGender

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role")
        )
    gender: Mapped[UserGender] = mapped_column(
        SQLEnum(UserGender, name="user_gender")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    face_embedding: Mapped[list[float] | None] = mapped_column(Vector(512))


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    x: Mapped[float]
    y: Mapped[float]
    capacity: Mapped[int]


class Timetable(Base):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(100))
    start: Mapped[datetime]
    end: Mapped[datetime]
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))


class Registered(Base):
    __tablename__ = "registered"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True,
    )
    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id"),
        primary_key=True,
    )

class Attendance(Base):
    __tablename__ = "attendance"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True,
    )

    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id"),
        primary_key=True,
    )

    checked_in_date: Mapped[date] = mapped_column(
        primary_key=True,
    )

    checked_in_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
    )
