from app.db.enums import DayOfWeek
from pydantic import BaseModel, ConfigDict
from datetime import time

class MyRegistrationResponse(BaseModel):
    id: int
    subject: str
    start: time
    end: time
    professor_name: str
    day_of_week: DayOfWeek
    room_id: str

    model_config = ConfigDict(from_attributes=True)
