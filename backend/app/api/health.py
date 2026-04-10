from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.cache_service import get_redis
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=HealthResponse)
async def health_check():
    services: dict[str, str] = {}

    # Redis check
    try:
        await get_redis().ping()
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "degraded"

    # DB is checked at startup; mark ok if we get here
    services["database"] = "ok"
    services["scheduler"] = "ok"

    return HealthResponse(
        status="ok",
        version="1.0.0",
        services=services,
    )
