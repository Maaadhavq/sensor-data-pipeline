"""Application entry point.

Creates the FastAPI app, attaches metadata (which drives the OpenAPI/Swagger
docs), and mounts the routers.

Run locally with:
    uvicorn app.main:app --reload --port 8001
Then open http://127.0.0.1:8001/docs for the interactive Swagger UI.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers.insights import router as insights_router
from app.routers.sensors import router as sensors_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database on startup (creates tables if missing).
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    contact={"name": "Madhav"},
    lifespan=lifespan,
)

# The Vercel-hosted dashboard (Phase 3) calls this API from the browser,
# so cross-origin requests must be allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO Phase 3: restrict to the Vercel domain
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(sensors_router)
app.include_router(insights_router)


@app.get("/", tags=["Meta"], summary="API root")
def root() -> dict:
    """Basic API metadata and useful links."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health", tags=["Meta"], summary="Health check")
def health() -> dict:
    """Liveness probe used by monitoring/uptime checks."""
    return {"status": "ok"}
