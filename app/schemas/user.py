from pydantic import BaseModel


class UserDataResponse(BaseModel):
    name: str
    role: str
    gender: str
    email: str
    has_image: bool
