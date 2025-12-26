from fastapi import APIRouter

from app.models import DeviceStatus, PortErrors
from app.services.monitor import monitor

router = APIRouter(prefix="/api", tags=["devices"])


@router.get("/devices", response_model=list[DeviceStatus])
async def get_all_devices():
    """Get status of all configured devices."""
    return monitor.get_all_devices()


@router.get("/devices/mismatched", response_model=list[DeviceStatus])
async def get_mismatched_devices():
    """Get devices with speed mismatches."""
    return monitor.get_mismatched_devices()


@router.get("/ports", response_model=list[PortErrors])
async def get_all_ports():
    """Get all port statistics."""
    return monitor.get_all_ports()


@router.get("/ports/errors", response_model=list[PortErrors])
async def get_ports_with_errors():
    """Get ports that have errors (dropped, corrupted frames)."""
    return monitor.get_ports_with_errors()
