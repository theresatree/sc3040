from app.db.enums import UserRole, UserGender
from pydantic import BaseModel, EmailStr
from fastapi import Form, File, UploadFile

class LoginRequest(BaseModel):
    email: str
    password: str

# For multipart form data with a file, declare ALL fields (incl. the file)
# inside the model and use Form(media_type="multipart/form-data") in the route
# (not Annotated - it would advertise urlencoded and break Swagger UI).

class RegisterRequest(BaseModel):
    name: str = Form(...)
    email: EmailStr = Form(...)
    password: str = Form(...)
    role: UserRole | None = Form(UserRole.STUDENT)
    gender: UserGender = Form(...)
    image: UploadFile = File(...)
    model_config = {"extra": "forbid"}
