from datetime import time
from pydantic import BaseModel, ConfigDict, model_validator

from app.db.enums import DayOfWeek

class RoomResponse(BaseModel):
    id: str
    name: str
    capacity: int

    model_config = ConfigDict(from_attributes=True)

class ProfessorResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class TimetableResponse(BaseModel):
    id: int
    subject: str
    start: time
    end: time
    day_of_week: DayOfWeek
    professor: ProfessorResponse
    room: RoomResponse
    registered_count: int

    model_config = ConfigDict(from_attributes=True)

class MyTimetableResponse(BaseModel):
    id: int
    subject: str
    start: time
    end: time
    day_of_week: DayOfWeek
    room: RoomResponse
    registered_count: int

    model_config = ConfigDict(from_attributes=True)

class UpdateMyTimetableRequest(BaseModel):
    subject: str | None = None
    start: time | None = None
    end: time | None = None
    day_of_week: DayOfWeek | None = None
    room_id: str | None = None
    
class TimetableRequest(BaseModel):
    subject: str
    start: time
    end: time
    day_of_week: DayOfWeek
    room_id: str

    
    @model_validator(mode="after")
    def validate_times(self):
        if self.start >= self.end:
            raise ValueError("Start time must be before end time")
        return self
