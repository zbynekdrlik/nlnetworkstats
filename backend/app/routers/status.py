from fastapi import APIRouter

from app.models import SwitchStatus, SystemStatus
from app.services.monitor import monitor

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status."""
    return monitor.get_system_status()


@router.get("/switches", response_model=list[SwitchStatus])
async def get_switches():
    """Get connection status of all switches."""
    return monitor.get_switch_statuses()


@router.post("/refresh")
async def refresh_data():
    """Force a data refresh."""
    monitor.collect_data()
    return {"status": "refreshed"}
