from fastapi import APIRouter

router = APIRouter(
    prefix="/register",
    tags=["register"],
)


@router.get("/")
async def get_registrations():
    return {"message": "registrations router works"}
