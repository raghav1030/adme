from app.core.config import settings


def get_health_status() -> dict:
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }
