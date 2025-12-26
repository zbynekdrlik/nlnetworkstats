import logging
from dataclasses import dataclass
from typing import Any

import librouteros
from librouteros import connect
from librouteros.exceptions import TrapError, ConnectionClosed, FatalError

from app.models import SwitchConfig

logger = logging.getLogger(__name__)


@dataclass
class ArpEntry:
    ip: str
    mac: str
    interface: str


@dataclass
class BridgeHost:
    mac: str
    interface: str
    bridge: str


@dataclass
class InterfaceInfo:
    name: str
    type: str
    running: bool
    speed: str | None
    rx_bytes: int
    tx_bytes: int
    rx_dropped: int
    tx_dropped: int
    rx_errors: int
    tx_errors: int
    rx_fcs_errors: int
    tx_fcs_errors: int


class MikroTikClient:
    """Client for communicating with MikroTik devices via RouterOS API."""

    def __init__(self, config: SwitchConfig):
        self.config = config
        self._api: librouteros.Api | None = None

    def connect(self) -> bool:
        """Establish connection to the MikroTik device."""
        try:
            self._api = connect(
                host=self.config.host,
                username=self.config.username,
                password=self.config.password,
                port=self.config.port,
            )
            logger.info(f"Connected to {self.config.name} ({self.config.host})")
            return True
        except (TrapError, ConnectionClosed, FatalError, OSError) as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            self._api = None
            return False

    def disconnect(self):
        """Close the connection."""
        if self._api:
            try:
                self._api.close()
            except Exception:
                pass
            self._api = None

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._api is not None

    def _query(self, path: str) -> list[dict[str, Any]]:
        """Execute a query and return results."""
        if not self._api:
            return []
        try:
            result = list(self._api.path(path))
            return result
        except (TrapError, ConnectionClosed, FatalError) as e:
            logger.error(f"Query failed on {self.config.name}: {e}")
            return []

    def get_arp_table(self) -> list[ArpEntry]:
        """Get the ARP table (IP to MAC mapping)."""
        entries = []
        for item in self._query("ip/arp"):
            if "address" in item and "mac-address" in item:
                entries.append(
                    ArpEntry(
                        ip=item.get("address", ""),
                        mac=item.get("mac-address", "").upper(),
                        interface=item.get("interface", ""),
                    )
                )
        return entries

    def get_bridge_hosts(self) -> list[BridgeHost]:
        """Get bridge hosts table (MAC to port mapping)."""
        hosts = []
        for item in self._query("interface/bridge/host"):
            if "mac-address" in item and "on-interface" in item:
                hosts.append(
                    BridgeHost(
                        mac=item.get("mac-address", "").upper(),
                        interface=item.get("on-interface", ""),
                        bridge=item.get("bridge", ""),
                    )
                )
        return hosts

    def get_interfaces(self) -> list[InterfaceInfo]:
        """Get interface information including speeds and statistics."""
        interfaces = []

        # Get ethernet interfaces with their speeds
        for item in self._query("interface/ethernet"):
            name = item.get("name", "")
            running = item.get("running", "false") == "true"
            speed = item.get("speed", None)

            # Get statistics
            stats = self._get_interface_stats(name)

            interfaces.append(
                InterfaceInfo(
                    name=name,
                    type="ethernet",
                    running=running,
                    speed=speed,
                    rx_bytes=stats.get("rx-byte", 0),
                    tx_bytes=stats.get("tx-byte", 0),
                    rx_dropped=stats.get("rx-drop", 0),
                    tx_dropped=stats.get("tx-drop", 0),
                    rx_errors=stats.get("rx-error", 0),
                    tx_errors=stats.get("tx-error", 0),
                    rx_fcs_errors=stats.get("rx-fcs-error", 0),
                    tx_fcs_errors=stats.get("tx-fcs-error", 0),
                )
            )

        return interfaces

    def _get_interface_stats(self, interface_name: str) -> dict[str, int]:
        """Get statistics for a specific interface."""
        if not self._api:
            return {}

        try:
            stats_path = self._api.path("interface")
            result = list(stats_path.select(".proplist=name,rx-byte,tx-byte,rx-drop,tx-drop,rx-error,tx-error,rx-fcs-error,tx-fcs-error").where(librouteros.query.Key("name") == interface_name))
            if result:
                item = result[0]
                return {
                    "rx-byte": int(item.get("rx-byte", 0)),
                    "tx-byte": int(item.get("tx-byte", 0)),
                    "rx-drop": int(item.get("rx-drop", 0)),
                    "tx-drop": int(item.get("tx-drop", 0)),
                    "rx-error": int(item.get("rx-error", 0)),
                    "tx-error": int(item.get("tx-error", 0)),
                    "rx-fcs-error": int(item.get("rx-fcs-error", 0)),
                    "tx-fcs-error": int(item.get("tx-fcs-error", 0)),
                }
        except Exception as e:
            logger.debug(f"Could not get stats for {interface_name}: {e}")

        return {}

    def get_all_data(self) -> dict[str, Any]:
        """Get all relevant data from the switch."""
        return {
            "arp": self.get_arp_table(),
            "bridge_hosts": self.get_bridge_hosts(),
            "interfaces": self.get_interfaces(),
        }
