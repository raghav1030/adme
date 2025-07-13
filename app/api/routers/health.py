from fastapi import APIRouter
from app.services.health import get_health_status

router = APIRouter()


@router.get("/health", response_model=dict)
async def health_check():
    return get_health_status()
