from datetime import datetime
from pydantic import BaseModel


class SwitchConfig(BaseModel):
    name: str
    host: str
    username: str
    password: str
    port: int = 8728


class DeviceConfig(BaseModel):
    name: str
    ip: str
    expected_speed: str
    mac: str | None = None     # Known MAC address (optional, for static IP devices)
    switch: str | None = None  # Expected switch name (optional)
    port: str | None = None    # Expected port name (optional)


class DeviceStatus(BaseModel):
    name: str
    ip: str
    mac: str | None = None
    expected_speed: str
    actual_speed: str | None = None
    switch_name: str | None = None
    port_name: str | None = None
    speed_match: bool = False
    online: bool = False
    last_seen: datetime | None = None


class PortErrors(BaseModel):
    switch_name: str
    port_name: str
    device_name: str | None = None  # Device connected to this port
    link_status: str = "unknown"
    speed: str | None = None
    full_duplex: bool = True
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    rx_fcs_errors: int = 0
    tx_fcs_errors: int = 0
    rx_pause: int = 0
    tx_pause: int = 0
    rx_fragment: int = 0
    has_issues: bool = False


class SwitchStatus(BaseModel):
    name: str
    host: str
    connected: bool
    error: str | None = None
    last_check: datetime | None = None


class SystemStatus(BaseModel):
    total_devices: int
    online_devices: int
    mismatched_speeds: int
    ports_with_errors: int
    switches_connected: int
    switches_total: int
    last_update: datetime | None = None
