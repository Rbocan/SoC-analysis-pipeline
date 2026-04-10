from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.settings import settings
from app.database import engine, Base
from app.middleware.audit import AuditMiddleware
from app.middleware.error_handler import register_exception_handlers
from app.api import data, reports, synthetic, products, auth, health, ml
from app.services.scheduler import start_scheduler, stop_scheduler
from app.config.loader import load_products_config

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting SoC Dashboard API")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    load_products_config()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    logger.info("SoC Dashboard API stopped")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="SoC Manufacturing Validation Dashboard API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

register_exception_handlers(app)

app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(synthetic.router, prefix="/api/synthetic", tags=["synthetic"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
