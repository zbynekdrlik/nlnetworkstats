import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import devices, status
from app.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting NLNetworkStats...")
    start_scheduler()
    yield
    logger.info("Shutting down NLNetworkStats...")
    stop_scheduler()


app = FastAPI(
    title="NLNetworkStats",
    description="Network monitoring for MikroTik switches",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(status.router)
app.include_router(devices.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "NLNetworkStats",
        "version": "1.0.0",
        "docs": "/docs",
    }
