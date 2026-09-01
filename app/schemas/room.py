from pydantic import BaseModel, field_validator

class RoomDataResponse(BaseModel):
    id: str
    name: str
    longitude: float
    latitude: float
    capacity: int


class CreateRoomRequest(BaseModel):
    id: str
    name: str
    longitude: float
    latitude: float
    capacity: int

    @field_validator("id")
    @classmethod
    def uppercase_id(cls, value: str) -> str:
        return value.upper()

class UpdateRoomRequest(BaseModel):
    id: str | None = None
    name: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    capacity: int | None = None

    @field_validator("id")
    @classmethod
    def uppercase_id(cls, value: str) -> str:
        return value.upper()

