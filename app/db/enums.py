from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    PROFESSOR = "professor"
    # STAFF = "staff"
    # ADMIN = "admin"

class UserGender(str, Enum):
    MALE = "male"
    FEMALE = "female"

class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
