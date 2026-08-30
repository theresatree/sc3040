from pydantic import BaseModel

class UserResponse(BaseModel):
    name: str
    role: str
    gender: str
    email: str
