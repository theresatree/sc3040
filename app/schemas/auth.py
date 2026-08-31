from app.db.enums import UserRole, UserGender
from pydantic import BaseModel, EmailStr
from fastapi import Form, File, UploadFile

class LoginRequest(BaseModel):
    email: str
    password: str

# Apparently because pydantic only works for JSON objects (application/json),
# We need multipart/form-data if we are including upload file
# Thus, we need Form and File
class RegisterRequest(BaseModel):
    name: str = Form(...)
    email: EmailStr = Form(...)
    password: str = Form(...)
    role: UserRole | None = Form(UserRole.STUDENT) # Default to student
    gender: UserGender = Form(...)
    image: UploadFile = File(...)
