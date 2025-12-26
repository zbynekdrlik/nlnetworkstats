import logging
from datetime import datetime

from app.config import load_devices, load_switches
from app.models import (
    DeviceConfig,
    DeviceStatus,
    PortErrors,
    SwitchConfig,
    SwitchStatus,
    SystemStatus,
)
from app.services.mikrotik import MikroTikClient

logger = logging.getLogger(__name__)


def normalize_speed(speed: str | None) -> str | None:
    """Normalize speed string for comparison."""
    if not speed:
        return None

    speed = speed.lower().strip()

    # Handle common formats
    if "gbps" in speed or "gbit" in speed or "1g" in speed:
        return "1Gbps"
    if "100m" in speed or "100-" in speed:
        return "100Mbps"
    if "10m" in speed or "10-" in speed:
        return "10Mbps"
    if "10g" in speed:
        return "10Gbps"
    if "2.5g" in speed:
        return "2.5Gbps"
    if "5g" in speed:
        return "5Gbps"

    return speed


class NetworkMonitor:
    """Monitors network devices and compares against expected configuration."""

    def __init__(self):
        self._switches: list[SwitchConfig] = []
        self._devices: list[DeviceConfig] = []
        self._device_statuses: dict[str, DeviceStatus] = {}
        self._port_errors: list[PortErrors] = []
        self._switch_statuses: dict[str, SwitchStatus] = {}
        self._last_update: datetime | None = None

    def reload_config(self):
        """Reload configuration from files."""
        self._switches = load_switches()
        self._devices = load_devices()
        logger.info(
            f"Loaded {len(self._switches)} switches and {len(self._devices)} devices"
        )

    def collect_data(self):
        """Collect data from all switches and update statuses."""
        if not self._switches:
            self.reload_config()

        # Initialize device statuses from config
        for device in self._devices:
            if device.ip not in self._device_statuses:
                self._device_statuses[device.ip] = DeviceStatus(
                    name=device.name,
                    ip=device.ip,
                    expected_speed=device.expected_speed,
                )

        # Reset online status
        for status in self._device_statuses.values():
            status.online = False
            status.mac = None
            status.switch_name = None
            status.port_name = None
            status.actual_speed = None
            status.speed_match = False

        self._port_errors = []

        # Collect data from each switch
        for switch_config in self._switches:
            self._collect_from_switch(switch_config)

        self._last_update = datetime.now()

    def _collect_from_switch(self, switch_config: SwitchConfig):
        """Collect data from a single switch."""
        client = MikroTikClient(switch_config)

        if not client.connect():
            self._switch_statuses[switch_config.name] = SwitchStatus(
                name=switch_config.name,
                host=switch_config.host,
                connected=False,
                error="Connection failed",
                last_check=datetime.now(),
            )
            return

        try:
            self._switch_statuses[switch_config.name] = SwitchStatus(
                name=switch_config.name,
                host=switch_config.host,
                connected=True,
                last_check=datetime.now(),
            )

            data = client.get_all_data()

            # Build MAC to IP mapping from ARP table
            mac_to_ip: dict[str, str] = {}
            for arp_entry in data["arp"]:
                mac_to_ip[arp_entry.mac] = arp_entry.ip

            # Build MAC to port mapping from bridge hosts
            mac_to_port: dict[str, str] = {}
            for host in data["bridge_hosts"]:
                mac_to_port[host.mac] = host.interface

            # Build port to speed mapping from interfaces
            port_info: dict[str, dict] = {}
            for iface in data["interfaces"]:
                port_info[iface.name] = {
                    "speed": iface.speed,
                    "running": iface.running,
                    "rx_dropped": iface.rx_dropped,
                    "tx_dropped": iface.tx_dropped,
                    "rx_errors": iface.rx_errors,
                    "tx_errors": iface.tx_errors,
                    "rx_fcs_errors": iface.rx_fcs_errors,
                    "tx_fcs_errors": iface.tx_fcs_errors,
                    "rx_bytes": iface.rx_bytes,
                    "tx_bytes": iface.tx_bytes,
                }

            # Update device statuses
            for mac, ip in mac_to_ip.items():
                if ip in self._device_statuses:
                    status = self._device_statuses[ip]
                    status.mac = mac
                    status.online = True
                    status.last_seen = datetime.now()

                    # Find the port for this MAC
                    if mac in mac_to_port:
                        port_name = mac_to_port[mac]
                        status.port_name = port_name
                        status.switch_name = switch_config.name

                        # Get speed for this port
                        if port_name in port_info:
                            actual_speed = port_info[port_name]["speed"]
                            status.actual_speed = normalize_speed(actual_speed)
                            expected = normalize_speed(status.expected_speed)
                            status.speed_match = status.actual_speed == expected

            # Collect port errors
            for iface in data["interfaces"]:
                has_issues = (
                    iface.rx_dropped > 0
                    or iface.tx_dropped > 0
                    or iface.rx_errors > 0
                    or iface.tx_errors > 0
                    or iface.rx_fcs_errors > 0
                    or iface.tx_fcs_errors > 0
                )

                self._port_errors.append(
                    PortErrors(
                        switch_name=switch_config.name,
                        port_name=iface.name,
                        link_status="up" if iface.running else "down",
                        speed=normalize_speed(iface.speed),
                        rx_bytes=iface.rx_bytes,
                        tx_bytes=iface.tx_bytes,
                        rx_dropped=iface.rx_dropped,
                        tx_dropped=iface.tx_dropped,
                        rx_errors=iface.rx_errors,
                        tx_errors=iface.tx_errors,
                        rx_fcs_errors=iface.rx_fcs_errors,
                        tx_fcs_errors=iface.tx_fcs_errors,
                        has_issues=has_issues,
                    )
                )

        finally:
            client.disconnect()

    def get_all_devices(self) -> list[DeviceStatus]:
        """Get status of all configured devices."""
        return list(self._device_statuses.values())

    def get_mismatched_devices(self) -> list[DeviceStatus]:
        """Get devices with speed mismatches."""
        return [
            status
            for status in self._device_statuses.values()
            if status.online and not status.speed_match
        ]

    def get_all_ports(self) -> list[PortErrors]:
        """Get all port statistics."""
        return self._port_errors

    def get_ports_with_errors(self) -> list[PortErrors]:
        """Get ports that have errors."""
        return [port for port in self._port_errors if port.has_issues]

    def get_switch_statuses(self) -> list[SwitchStatus]:
        """Get connection status of all switches."""
        return list(self._switch_statuses.values())

    def get_system_status(self) -> SystemStatus:
        """Get overall system status."""
        devices = list(self._device_statuses.values())
        online_devices = [d for d in devices if d.online]
        mismatched = [d for d in online_devices if not d.speed_match]
        ports_with_errors = [p for p in self._port_errors if p.has_issues]
        switches_connected = [
            s for s in self._switch_statuses.values() if s.connected
        ]

        return SystemStatus(
            total_devices=len(devices),
            online_devices=len(online_devices),
            mismatched_speeds=len(mismatched),
            ports_with_errors=len(ports_with_errors),
            switches_connected=len(switches_connected),
            switches_total=len(self._switches),
            last_update=self._last_update,
        )


# Global monitor instance
monitor = NetworkMonitor()
