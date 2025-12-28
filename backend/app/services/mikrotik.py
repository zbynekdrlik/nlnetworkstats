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
    full_duplex: bool
    rx_bytes: int
    tx_bytes: int
    rx_dropped: int
    tx_dropped: int
    rx_errors: int
    tx_errors: int
    rx_fcs_errors: int
    tx_fcs_errors: int
    rx_pause: int
    tx_pause: int
    rx_fragment: int


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

        # Get ethernet interfaces
        for item in self._query("interface/ethernet"):
            name = item.get("name", "")
            running = item.get("running", False) is True

            # Get actual link speed and duplex from monitor
            speed, full_duplex = self._get_interface_monitor(name) if running else (None, True)

            # Get statistics
            stats = self._get_interface_stats(name)

            interfaces.append(
                InterfaceInfo(
                    name=name,
                    type="ethernet",
                    running=running,
                    speed=speed,
                    full_duplex=full_duplex,
                    rx_bytes=stats.get("rx-byte", 0),
                    tx_bytes=stats.get("tx-byte", 0),
                    rx_dropped=stats.get("rx-drop", 0),
                    tx_dropped=stats.get("tx-drop", 0),
                    rx_errors=stats.get("rx-error", 0),
                    tx_errors=stats.get("tx-error", 0),
                    rx_fcs_errors=stats.get("rx-fcs-error", 0),
                    tx_fcs_errors=stats.get("tx-fcs-error", 0),
                    rx_pause=stats.get("rx-pause", 0),
                    tx_pause=stats.get("tx-pause", 0),
                    rx_fragment=stats.get("rx-fragment", 0),
                )
            )

        return interfaces

    def _get_interface_monitor(self, interface_name: str) -> tuple[str | None, bool]:
        """Get actual link speed and duplex from interface monitor."""
        if not self._api:
            return None, True

        try:
            # Use the monitor command with once=True to get current status
            monitor_path = self._api.path("interface/ethernet")
            result = list(monitor_path("monitor", **{"numbers": interface_name, "once": ""}))
            if result:
                rate = result[0].get("rate", None)
                full_duplex = result[0].get("full-duplex", True)
                return rate, full_duplex
        except Exception as e:
            logger.warning(f"Could not get monitor for {interface_name}: {e}")

        return None, True

    def _get_interface_stats(self, interface_name: str) -> dict[str, int]:
        """Get statistics for a specific interface."""
        if not self._api:
            return {}

        try:
            # Get stats from interface/ethernet which has all the detailed counters
            for item in self._query("interface/ethernet"):
                if item.get("name") == interface_name:
                    return {
                        "rx-byte": int(item.get("rx-bytes", 0)),
                        "tx-byte": int(item.get("tx-bytes", 0)),
                        "rx-drop": int(item.get("rx-overflow", 0)),
                        "tx-drop": int(item.get("tx-drop-packet", 0)),
                        "rx-error": int(item.get("rx-error-events", 0)),
                        "tx-error": int(item.get("tx-underrun", 0)),
                        "rx-fcs-error": int(item.get("rx-fcs-error", 0)),
                        "tx-fcs-error": int(item.get("tx-collision", 0) + item.get("tx-late-collision", 0)),
                        "rx-pause": int(item.get("rx-pause", 0)),
                        "tx-pause": int(item.get("tx-pause", 0)),
                        "rx-fragment": int(item.get("rx-fragment", 0)),
                    }
        except Exception as e:
            logger.debug(f"Could not get stats for {interface_name}: {e}")

        return {}

    def get_identity(self) -> str:
        """Get the switch identity (name configured on the device)."""
        if not self._api:
            return self.config.name

        try:
            result = list(self._api.path("system/identity"))
            if result:
                return result[0].get("name", self.config.name)
        except Exception as e:
            logger.warning(f"Could not get identity: {e}")

        return self.config.name

    def get_dhcp_leases(self) -> dict[str, str]:
        """Get DHCP leases (IP to MAC mapping).

        Returns a dict mapping IP -> MAC address for all DHCP leases.
        This provides IP->MAC mappings even for devices not in ARP table.
        """
        leases: dict[str, str] = {}
        if not self._api:
            return leases

        try:
            for lease in self._api.path("ip/dhcp-server/lease"):
                ip = lease.get("address", "")
                mac = lease.get("mac-address", "").upper()
                if ip and mac:
                    leases[ip] = mac
        except Exception as e:
            logger.debug(f"Could not get DHCP leases (might not be a DHCP server): {e}")

        return leases

    def get_uplink_ports(self) -> dict[str, str]:
        """Get ports that connect to other switches (uplinks) using neighbor discovery.

        Returns a dict mapping port name -> neighbor identity (switch name).
        """
        uplinks: dict[str, str] = {}
        if not self._api:
            return uplinks

        try:
            for neighbor in self._api.path("ip/neighbor"):
                # If neighbor has an identity, it's likely another network device (switch/router)
                identity = neighbor.get("identity", "")
                if identity:  # Has identity = network device = uplink port
                    interface = neighbor.get("interface", "")
                    # Extract port name (remove ",bridge" suffix)
                    port = interface.split(",")[0] if "," in interface else interface
                    if port and port != "bridge":
                        uplinks[port] = identity
        except Exception as e:
            logger.warning(f"Could not get neighbors: {e}")

        return uplinks

    def ping_check(self, ip: str) -> bool:
        """Ping an IP address and return True if reachable."""
        if not self._api:
            return False

        try:
            results = list(self._api("/ping", address=ip, count="1"))
            # Check if we got a response
            for result in results:
                if result.get("received", 0) > 0:
                    return True
            return False
        except Exception as e:
            logger.debug(f"Ping to {ip} failed: {e}")
            return False

    def ping_multiple(self, ip_addresses: list[str]) -> dict[str, bool]:
        """Ping multiple IP addresses and return reachability status."""
        results: dict[str, bool] = {}
        for ip in ip_addresses:
            results[ip] = self.ping_check(ip)
        return results

    def get_all_data(self) -> dict[str, Any]:
        """Get all relevant data from the switch."""
        return {
            "identity": self.get_identity(),
            "arp": self.get_arp_table(),
            "dhcp_leases": self.get_dhcp_leases(),
            "bridge_hosts": self.get_bridge_hosts(),
            "interfaces": self.get_interfaces(),
            "uplink_ports": self.get_uplink_ports(),
        }
