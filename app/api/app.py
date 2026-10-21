"""
DataPulse AI - FastAPI Application Factory
Initializes FastAPI server, middleware, routes, and startup lifecycle.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import logger
from app.monitoring.metrics import PlatformMonitor
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database initialization and warmup."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    try:
        init_db()
        logger.info("Database schema validated.")
    except Exception as e:
        logger.error(f"Startup database initialization error: {e}")
    yield
    logger.info("Shutting down DataPulse AI...")


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application instance."""
    app = FastAPI(
        title="DataPulse AI Platform API",
        description=(
            "Production-Grade Data Engineering and Predictive Analytics Platform API. "
            "Supports automated batch ingestion, schema validation, quarantine tracking, "
            "dimensional warehousing, sales forecasting, and anomaly detection."
        ),
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Enable CORS for dashboard and external frontends
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health Check Endpoint
    @app.get("/health", tags=["System Health"])
    def health_check():
        """Returns platform operational health and database connectivity."""
        return PlatformMonitor.get_system_health()

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX, tags=["DataPulse API v1"])

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.app:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)
