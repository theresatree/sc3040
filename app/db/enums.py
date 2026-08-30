from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"

class UserGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
