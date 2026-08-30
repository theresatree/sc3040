from fastapi import APIRouter

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
)


@router.get("/")
async def get_rooms():
    return {"message": "rooms router works"}
