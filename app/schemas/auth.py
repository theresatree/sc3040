from app.db.enums import UserRole
from pydantic import BaseModel, EmailStr
from app.db.enums import UserGender

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    gender: UserGender
    role: UserRole | None
    email: EmailStr
    password: str
