import logging
import socket
from collections import deque
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
from app.services.webhook import send_webhook_sync

logger = logging.getLogger(__name__)


def normalize_speed(speed: str | None) -> str | None:
    """Normalize speed string for comparison."""
    if not speed:
        return None

    speed = speed.lower().strip()

    # Handle common formats (order matters - check specific patterns first!)
    if "10g" in speed:
        return "10Gbps"
    if "2.5g" in speed:  # Must check before "5g" since "2.5g" contains "5g"
        return "2.5Gbps"
    if "5g" in speed:
        return "5Gbps"
    if "1g" in speed or "gbps" in speed or "gbit" in speed:
        return "1Gbps"
    if "100m" in speed or "100-" in speed:
        return "100Mbps"
    if "10m" in speed or "10-" in speed:
        return "10Mbps"

    return speed


def resolve_hostname(hostname: str) -> str:
    """Resolve hostname to IP address. Returns original if already an IP or resolution fails."""
    # Check if it's already an IP address
    try:
        socket.inet_aton(hostname)
        return hostname  # Already an IP
    except socket.error:
        pass

    # Try to resolve DNS name
    try:
        ip = socket.gethostbyname(hostname)
        logger.debug(f"Resolved {hostname} -> {ip}")
        return ip
    except socket.gaierror:
        logger.warning(f"Could not resolve hostname: {hostname}")
        return hostname  # Return original if resolution fails


class NetworkMonitor:
    """Monitors network devices and compares against expected configuration."""

    def __init__(self):
        self._switches: list[SwitchConfig] = []
        self._devices: list[DeviceConfig] = []
        self._device_statuses: dict[str, DeviceStatus] = {}
        self._port_errors: list[PortErrors] = []
        self._switch_statuses: dict[str, SwitchStatus] = {}
        self._last_update: datetime | None = None
        # State tracking for webhooks
        self._previous_mismatched_ips: set[str] = set()
        self._previous_online_ips: set[str] = set()
        # Track port error history: port_key -> deque of last 3 total error counts
        self._port_error_history: dict[str, deque] = {}
        # Track last notification time for each port (30 min cooldown)
        self._port_error_last_notified: dict[str, datetime] = {}
        # Cooldown period in minutes before sending another notification for same port
        self._notification_cooldown_minutes: int = 30

    def reload_config(self):
        """Reload configuration from files."""
        self._switches = load_switches()
        self._devices = load_devices()
        logger.info(
            f"Loaded {len(self._switches)} switches and {len(self._devices)} devices"
        )

    def _verify_online_with_ping(self, device_statuses: dict[str, DeviceStatus]):
        """Verify online devices are actually reachable via ping.

        This catches devices that appear in stale ARP/bridge tables but are offline.
        Uses the first switch (router) which can reach all subnets.
        """
        if not self._switches:
            return

        # Get resolved IPs of devices currently marked as online
        # We need to ping the resolved IP, not the DNS name
        online_resolved_ips = []
        for resolved_ip, status in device_statuses.items():
            if status.online:
                online_resolved_ips.append(resolved_ip)

        if not online_resolved_ips:
            return

        # Connect to router (first switch) to ping devices
        router_config = self._switches[0]
        client = MikroTikClient(router_config)

        if client.connect():
            try:
                ping_results = client.ping_multiple(online_resolved_ips)
                # Mark unreachable devices as offline
                for ip, reachable in ping_results.items():
                    if not reachable and ip in device_statuses:
                        status = device_statuses[ip]
                        logger.info(f"Device {status.name} ({ip}) failed ping check - marking offline")
                        status.online = False
            finally:
                client.disconnect()

    def collect_data(self):
        """Collect data from all switches and update statuses."""
        if not self._switches:
            self.reload_config()

        # Build lookup for configured switch/port per device
        # Resolve DNS names to IPs for matching against ARP table
        # Use fresh dicts to avoid showing incomplete data during collection
        device_config: dict[str, DeviceConfig] = {}
        device_statuses: dict[str, DeviceStatus] = {}
        for device in self._devices:
            resolved_ip = resolve_hostname(device.ip)
            if resolved_ip != device.ip:
                logger.info(f"Resolved {device.name}: {device.ip} -> {resolved_ip}")
            device_config[resolved_ip] = device
            # Preserve last_seen from previous status if exists
            old_status = self._device_statuses.get(resolved_ip)
            device_statuses[resolved_ip] = DeviceStatus(
                name=device.name,
                ip=device.ip,  # Keep original (DNS name or IP) for display
                expected_speed=device.expected_speed,
                last_seen=old_status.last_seen if old_status else None,
            )

        # Use local variables during collection, swap at the end
        self._device_config = device_config
        port_errors: list[PortErrors] = []

        # First pass: collect all IP->MAC mappings from all switches
        all_mac_to_ip: dict[str, str] = {}
        all_ip_to_mac: dict[str, str] = {}  # Reverse mapping for device lookup
        switch_data: list[tuple[SwitchConfig, dict]] = []

        # Pre-populate with configured MACs (for static IP devices not in ARP/DHCP)
        for device in self._devices:
            if device.mac:
                mac = device.mac.upper()
                all_mac_to_ip[mac] = device.ip
                all_ip_to_mac[device.ip] = mac
                logger.debug(f"Using configured MAC for {device.name}: {mac}")

        for switch_config in self._switches:
            client = MikroTikClient(switch_config)
            if client.connect():
                try:
                    data = client.get_all_data()
                    switch_data.append((switch_config, data))
                    # Collect ARP entries (overrides configured MACs if present)
                    for arp_entry in data["arp"]:
                        all_mac_to_ip[arp_entry.mac] = arp_entry.ip
                        all_ip_to_mac[arp_entry.ip] = arp_entry.mac
                    # Collect DHCP leases (additional IP->MAC source)
                    dhcp_leases = data.get("dhcp_leases", {})
                    for ip, mac in dhcp_leases.items():
                        if mac not in all_mac_to_ip:  # Don't overwrite ARP
                            all_mac_to_ip[mac] = ip
                        if ip not in all_ip_to_mac:  # Don't overwrite ARP
                            all_ip_to_mac[ip] = mac
                finally:
                    client.disconnect()

        # Second pass: find devices on access ports
        for switch_config, data in switch_data:
            self._process_switch_data(switch_config, data, all_mac_to_ip, device_statuses, port_errors)

        # Third pass: verify online status with ping from router
        # This catches devices that appear in stale ARP/bridge tables but are actually offline
        self._verify_online_with_ping(device_statuses)

        # Atomically swap the new data (prevents showing incomplete data during collection)
        self._device_statuses = device_statuses
        self._port_errors = port_errors
        self._last_update = datetime.now()

        # Check for state changes and send webhooks
        self._check_offline_changes()
        self._check_mismatched_changes()
        self._check_port_error_trends()

    def _process_switch_data(
        self,
        switch_config: SwitchConfig,
        data: dict,
        all_mac_to_ip: dict[str, str],
        device_statuses: dict[str, DeviceStatus],
        port_errors: list[PortErrors],
    ):
        """Process collected data from a switch."""
        switch_identity = data.get("identity", switch_config.name)

        self._switch_statuses[switch_config.name] = SwitchStatus(
            name=switch_identity,
            host=switch_config.host,
            connected=True,
            last_check=datetime.now(),
        )

        # Build MAC to port mapping from bridge hosts
        mac_to_port: dict[str, str] = {}
        for host in data["bridge_hosts"]:
            mac_to_port[host.mac] = host.interface

        # Get uplink ports from neighbor discovery (port -> neighbor identity)
        uplink_ports: dict[str, str] = data.get("uplink_ports", {})
        logger.info(f"{switch_identity}: uplink ports: {uplink_ports}")

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
                "full_duplex": iface.full_duplex,
                "rx_pause": iface.rx_pause,
                "tx_pause": iface.tx_pause,
                "rx_fragment": iface.rx_fragment,
            }

        # Update device statuses - iterate through bridge hosts
        for mac, port_name in mac_to_port.items():
            ip = all_mac_to_ip.get(mac)
            if ip and ip in device_statuses:
                status = device_statuses[ip]
                device_cfg = self._device_config.get(ip)
                status.mac = mac
                status.online = True
                status.last_seen = datetime.now()

                # Check if device has configured switch/port
                if device_cfg and device_cfg.switch and device_cfg.port:
                    if device_cfg.switch == switch_identity:
                        status.port_name = device_cfg.port
                        status.switch_name = switch_identity
                        if device_cfg.port in port_info:
                            actual_speed = port_info[device_cfg.port]["speed"]
                            status.actual_speed = normalize_speed(actual_speed)
                            expected = normalize_speed(status.expected_speed)
                            status.speed_match = status.actual_speed == expected
                else:
                    # Auto-discover: only use access ports (not uplinks)
                    is_access_port = port_name not in uplink_ports
                    if is_access_port and status.port_name is None:
                        status.port_name = port_name
                        status.switch_name = switch_identity
                        if port_name in port_info:
                            actual_speed = port_info[port_name]["speed"]
                            status.actual_speed = normalize_speed(actual_speed)
                            expected = normalize_speed(status.expected_speed)
                            status.speed_match = status.actual_speed == expected

        # Build port -> device name mapping (includes switches from neighbor discovery)
        port_to_device: dict[str, str] = {}
        # First add switches from neighbor discovery (exclude basic_switch)
        for port, neighbor_identity in uplink_ports.items():
            if "basic_switch" not in neighbor_identity.lower():
                port_to_device[port] = neighbor_identity
        # Then add devices (may override if a device is on an uplink port)
        for status in device_statuses.values():
            if status.switch_name == switch_identity and status.port_name:
                port_to_device[status.port_name] = status.name

        # Collect port errors - flag any non-zero error counters
        for iface in data["interfaces"]:
            has_issues = (
                iface.rx_dropped > 0
                or iface.tx_dropped > 0
                or iface.rx_errors > 0
                or iface.tx_errors > 0
                or iface.rx_fcs_errors > 0
                or iface.tx_fcs_errors > 0
                or iface.rx_pause > 0
                or iface.rx_fragment > 0
                or not iface.full_duplex  # Half duplex is a problem
            )

            port_errors.append(
                PortErrors(
                    switch_name=switch_identity,
                    port_name=iface.name,
                    device_name=port_to_device.get(iface.name),
                    link_status="up" if iface.running else "down",
                    speed=normalize_speed(iface.speed),
                    full_duplex=iface.full_duplex,
                    rx_bytes=iface.rx_bytes,
                    tx_bytes=iface.tx_bytes,
                    rx_dropped=iface.rx_dropped,
                    tx_dropped=iface.tx_dropped,
                    rx_errors=iface.rx_errors,
                    tx_errors=iface.tx_errors,
                    rx_fcs_errors=iface.rx_fcs_errors,
                    tx_fcs_errors=iface.tx_fcs_errors,
                    rx_pause=iface.rx_pause,
                    tx_pause=iface.tx_pause,
                    rx_fragment=iface.rx_fragment,
                    has_issues=has_issues,
                )
            )

    def _collect_from_switch(self, switch_config: SwitchConfig):
        """Collect data from a single switch (legacy - kept for reference)."""
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
            data = client.get_all_data()
            switch_identity = data.get("identity", switch_config.name)

            self._switch_statuses[switch_config.name] = SwitchStatus(
                name=switch_identity,
                host=switch_config.host,
                connected=True,
                last_check=datetime.now(),
            )

            # Build MAC to IP mapping from ARP table
            mac_to_ip: dict[str, str] = {}
            for arp_entry in data["arp"]:
                mac_to_ip[arp_entry.mac] = arp_entry.ip

            # Build MAC to port mapping from bridge hosts
            mac_to_port: dict[str, str] = {}
            for host in data["bridge_hosts"]:
                mac_to_port[host.mac] = host.interface

            # Get uplink ports from neighbor discovery (ports connected to other switches)
            uplink_ports: dict[str, str] = data.get("uplink_ports", {})
            logger.info(f"{switch_identity}: uplink ports (neighbor discovery): {uplink_ports}")

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
                    device_cfg = self._device_config.get(ip)
                    status.mac = mac
                    status.online = True
                    status.last_seen = datetime.now()

                    # Check if device has configured switch/port
                    if device_cfg and device_cfg.switch and device_cfg.port:
                        # Use configured switch/port if this is the right switch
                        if device_cfg.switch == switch_identity:
                            status.port_name = device_cfg.port
                            status.switch_name = switch_identity

                            # Get speed for configured port
                            if device_cfg.port in port_info:
                                actual_speed = port_info[device_cfg.port]["speed"]
                                status.actual_speed = normalize_speed(actual_speed)
                                expected = normalize_speed(status.expected_speed)
                                status.speed_match = status.actual_speed == expected
                    else:
                        # Auto-discover: find the port for this MAC
                        if mac in mac_to_port:
                            port_name = mac_to_port[mac]

                            # Only consider access ports (few MACs = direct connection)
                            is_access_port = port_name not in uplink_ports

                            # Only update if this is an access port AND we don't already have one
                            if is_access_port and status.port_name is None:
                                status.port_name = port_name
                                status.switch_name = switch_identity

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
                        switch_name=switch_identity,
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
        """Get devices with speed mismatches (only if actual speed is detected)."""
        return [
            status
            for status in self._device_statuses.values()
            if status.online and status.actual_speed and not status.speed_match
        ]

    def get_matched_devices(self) -> list[DeviceStatus]:
        """Get devices with matching speeds, sorted by IP."""
        devices = [
            status
            for status in self._device_statuses.values()
            if status.online and status.speed_match
        ]
        return sorted(devices, key=lambda d: tuple(int(p) for p in d.ip.split('.')))

    def get_offline_devices(self) -> list[DeviceStatus]:
        """Get devices that are offline."""
        return [
            status
            for status in self._device_statuses.values()
            if not status.online
        ]

    def get_all_ports(self) -> list[PortErrors]:
        """Get all port statistics."""
        return self._port_errors

    def get_ports_with_errors(self) -> list[PortErrors]:
        """Get ports that have errors."""
        return [port for port in self._port_errors if port.has_issues]

    def get_healthy_ports(self) -> list[PortErrors]:
        """Get all active ports (link up), sorted by switch then by traffic."""
        active = [port for port in self._port_errors if port.link_status == "up"]
        # Sort by switch name, then by total traffic (highest first)
        return sorted(active, key=lambda p: (p.switch_name, -(p.rx_bytes + p.tx_bytes)))

    def get_switch_statuses(self) -> list[SwitchStatus]:
        """Get connection status of all switches."""
        return list(self._switch_statuses.values())

    def get_system_status(self) -> SystemStatus:
        """Get overall system status."""
        devices = list(self._device_statuses.values())
        online_devices = [d for d in devices if d.online]
        mismatched = [d for d in online_devices if d.actual_speed and not d.speed_match]
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

    def _check_offline_changes(self):
        """Check for devices going offline or coming online and send webhooks."""
        current_online = set()
        for device in self._device_statuses.values():
            if device.online:
                current_online.add(device.ip)

        # Find devices that went offline
        went_offline = self._previous_online_ips - current_online
        for ip in went_offline:
            device = self._device_statuses.get(ip)
            if device:
                logger.warning(f"Device {device.name} went offline")
                send_webhook_sync("device_offline", {
                    "action": "device_offline",
                    "device": {
                        "name": device.name,
                        "ip": device.ip,
                        "mac": device.mac,
                        "expected_speed": device.expected_speed,
                        "actual_speed": device.actual_speed,
                        "switch_name": device.switch_name,
                        "port_name": device.port_name,
                        "online": device.online,
                        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    },
                    "message": f"Device went offline: {device.name} ({device.ip})",
                })

        # Find devices that came back online
        came_online = current_online - self._previous_online_ips
        for ip in came_online:
            device = self._device_statuses.get(ip)
            if device and self._previous_online_ips:  # Only notify if we had previous state
                logger.info(f"Device {device.name} came back online")
                send_webhook_sync("device_online", {
                    "action": "device_online",
                    "device": {
                        "name": device.name,
                        "ip": device.ip,
                        "mac": device.mac,
                        "expected_speed": device.expected_speed,
                        "actual_speed": device.actual_speed,
                        "switch_name": device.switch_name,
                        "port_name": device.port_name,
                        "online": device.online,
                        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    },
                    "message": f"Device came back online: {device.name} ({device.ip})",
                })

        # Update previous state
        self._previous_online_ips = current_online

    def _check_mismatched_changes(self):
        """Check for devices entering or leaving the mismatched state and send webhooks."""
        current_mismatched = set()
        mismatched_devices = self.get_mismatched_devices()

        for device in mismatched_devices:
            current_mismatched.add(device.ip)

        # Find newly mismatched devices
        new_mismatched = current_mismatched - self._previous_mismatched_ips
        for ip in new_mismatched:
            device = self._device_statuses.get(ip)
            if device:
                logger.info(f"Device {device.name} entered mismatched state")
                send_webhook_sync("device_speed_mismatch", {
                    "action": "mismatch_detected",
                    "device": {
                        "name": device.name,
                        "ip": device.ip,
                        "mac": device.mac,
                        "expected_speed": device.expected_speed,
                        "actual_speed": device.actual_speed,
                        "switch_name": device.switch_name,
                        "port_name": device.port_name,
                        "online": device.online,
                        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    },
                    "message": f"Speed mismatch detected: {device.name} expected {device.expected_speed} but got {device.actual_speed}",
                })

        # Find devices that left mismatched state (now fixed)
        fixed_devices = self._previous_mismatched_ips - current_mismatched
        for ip in fixed_devices:
            device = self._device_statuses.get(ip)
            if device:
                logger.info(f"Device {device.name} speed mismatch fixed")
                send_webhook_sync("device_speed_mismatch", {
                    "action": "mismatch_fixed",
                    "device": {
                        "name": device.name,
                        "ip": device.ip,
                        "mac": device.mac,
                        "expected_speed": device.expected_speed,
                        "actual_speed": device.actual_speed,
                        "switch_name": device.switch_name,
                        "port_name": device.port_name,
                        "online": device.online,
                        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    },
                    "message": f"Speed mismatch fixed: {device.name} now running at expected speed",
                })

        # Update previous state
        self._previous_mismatched_ips = current_mismatched

    def _check_port_error_trends(self):
        """Check for ports with rising error counts (3 consecutive increases) and send webhooks."""
        for port in self._port_errors:
            port_key = f"{port.switch_name}:{port.port_name}"

            # Calculate total errors for this port
            total_errors = (
                port.rx_dropped + port.tx_dropped +
                port.rx_errors + port.tx_errors +
                port.rx_fcs_errors + port.tx_fcs_errors +
                port.rx_pause + port.tx_pause +
                port.rx_fragment
            )

            # Initialize history if not exists
            if port_key not in self._port_error_history:
                self._port_error_history[port_key] = deque(maxlen=3)

            history = self._port_error_history[port_key]
            history.append(total_errors)

            # Check if we have 3 readings and all are rising
            if len(history) == 3:
                # Check if each reading is higher than the previous
                is_rising = history[0] < history[1] < history[2]

                if is_rising:
                    # Check cooldown - only notify if enough time has passed
                    last_notified = self._port_error_last_notified.get(port_key)
                    now = datetime.now()
                    cooldown_passed = (
                        last_notified is None or
                        (now - last_notified).total_seconds() > self._notification_cooldown_minutes * 60
                    )

                    if cooldown_passed:
                        # Trigger webhook - errors rising for 3 consecutive readings
                        logger.warning(f"Port {port_key} errors rising: {list(history)}")
                        send_webhook_sync("port_errors_rising", {
                            "action": "errors_increasing",
                            "port": {
                                "switch_name": port.switch_name,
                                "port_name": port.port_name,
                                "device_name": port.device_name,
                                "link_status": port.link_status,
                                "speed": port.speed,
                                "full_duplex": port.full_duplex,
                                "rx_bytes": port.rx_bytes,
                                "tx_bytes": port.tx_bytes,
                                "rx_dropped": port.rx_dropped,
                                "tx_dropped": port.tx_dropped,
                                "rx_errors": port.rx_errors,
                                "tx_errors": port.tx_errors,
                                "rx_fcs_errors": port.rx_fcs_errors,
                                "tx_fcs_errors": port.tx_fcs_errors,
                                "rx_pause": port.rx_pause,
                                "tx_pause": port.tx_pause,
                                "rx_fragment": port.rx_fragment,
                                "has_issues": port.has_issues,
                            },
                            "error_history": list(history),
                            "cooldown_minutes": self._notification_cooldown_minutes,
                            "message": f"Port {port.switch_name}/{port.port_name} ({port.device_name or 'unknown device'}) errors rising for 3 consecutive readings: {list(history)}",
                        })
                        # Record notification time for cooldown
                        self._port_error_last_notified[port_key] = now


# Global monitor instance
monitor = NetworkMonitor()
