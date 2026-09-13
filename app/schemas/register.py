from datetime import time

from pydantic import BaseModel, ConfigDict

from app.db.enums import DayOfWeek


class TimetableData(BaseModel):
    subject: str
    start: time
    end: time
    day_of_week: DayOfWeek
    room_id: str

    model_config = ConfigDict(from_attributes=True)


class RegistrationData(BaseModel):
    timetable_id: int
    timetable: TimetableData

    model_config = ConfigDict(from_attributes=True)
