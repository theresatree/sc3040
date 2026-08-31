from fastapi import UploadFile, File
from pydantic import BaseModel

class CheckInRequest(BaseModel):
    image: UploadFile = File(...)
