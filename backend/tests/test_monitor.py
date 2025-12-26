import pytest

from app.services.monitor import normalize_speed, NetworkMonitor


class TestNormalizeSpeed:
    """Test speed normalization function."""

    def test_normalize_1gbps_variations(self):
        """Test various 1Gbps formats."""
        assert normalize_speed("1Gbps") == "1Gbps"
        assert normalize_speed("1gbps") == "1Gbps"
        assert normalize_speed("1Gbit") == "1Gbps"
        assert normalize_speed("1G") == "1Gbps"

    def test_normalize_100mbps_variations(self):
        """Test various 100Mbps formats."""
        assert normalize_speed("100Mbps") == "100Mbps"
        assert normalize_speed("100mbps") == "100Mbps"
        assert normalize_speed("100M") == "100Mbps"
        assert normalize_speed("100-full") == "100Mbps"

    def test_normalize_10mbps_variations(self):
        """Test various 10Mbps formats."""
        assert normalize_speed("10Mbps") == "10Mbps"
        assert normalize_speed("10M") == "10Mbps"
        assert normalize_speed("10-full") == "10Mbps"

    def test_normalize_10gbps(self):
        """Test 10Gbps format."""
        assert normalize_speed("10Gbps") == "10Gbps"
        assert normalize_speed("10G") == "10Gbps"

    def test_normalize_none(self):
        """Test None input."""
        assert normalize_speed(None) is None

    def test_normalize_empty(self):
        """Test empty string."""
        assert normalize_speed("") is None

    def test_normalize_unknown(self):
        """Test unknown format returns as-is."""
        assert normalize_speed("unknown") == "unknown"


class TestNetworkMonitor:
    """Test NetworkMonitor class."""

    def test_init(self):
        """Test monitor initialization."""
        monitor = NetworkMonitor()
        assert monitor._switches == []
        assert monitor._devices == []
        assert monitor._device_statuses == {}

    def test_get_empty_devices(self):
        """Test getting devices when none configured."""
        monitor = NetworkMonitor()
        assert monitor.get_all_devices() == []

    def test_get_empty_mismatched(self):
        """Test getting mismatched devices when none exist."""
        monitor = NetworkMonitor()
        assert monitor.get_mismatched_devices() == []

    def test_get_empty_ports(self):
        """Test getting ports when none collected."""
        monitor = NetworkMonitor()
        assert monitor.get_all_ports() == []

    def test_get_empty_ports_with_errors(self):
        """Test getting ports with errors when none exist."""
        monitor = NetworkMonitor()
        assert monitor.get_ports_with_errors() == []

    def test_get_system_status_empty(self):
        """Test getting system status when empty."""
        monitor = NetworkMonitor()
        status = monitor.get_system_status()
        assert status.total_devices == 0
        assert status.online_devices == 0
        assert status.mismatched_speeds == 0
        assert status.ports_with_errors == 0
