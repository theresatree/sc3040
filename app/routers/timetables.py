from fastapi import APIRouter

router = APIRouter(
    prefix="/timetables",
    tags=["timetables"],
)


@router.get("/")
async def get_timetables():
    return {"message": "timetables router works"}
