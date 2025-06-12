from fastapi import APIRouter

router = APIRouter()

@router.get("/")
@router.get("")
async def health_check():
    return {"status": "healthy", "service": "relevia-api"}