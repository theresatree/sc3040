from pydantic import BaseModel
from fastapi import UploadFile, File

class UserDataResponse(BaseModel):
    name: str
    role: str
    gender: str
    email: str

class UserPasswordUpdateRequest(BaseModel):
    curr_password: str
    password: str

class UserImageUpdateRquest(BaseModel):
    image: UploadFile = File(...)
