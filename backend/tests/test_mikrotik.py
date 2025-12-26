import pytest
from unittest.mock import MagicMock, patch

from app.models import SwitchConfig
from app.services.mikrotik import MikroTikClient, ArpEntry, BridgeHost, InterfaceInfo


@pytest.fixture
def switch_config():
    """Create a test switch configuration."""
    return SwitchConfig(
        name="test-switch",
        host="192.168.1.1",
        username="admin",
        password="admin",
        port=8728,
    )


class TestMikroTikClient:
    """Test MikroTik client."""

    def test_init(self, switch_config):
        """Test client initialization."""
        client = MikroTikClient(switch_config)
        assert client.config == switch_config
        assert client._api is None

    def test_is_connected_false(self, switch_config):
        """Test is_connected when not connected."""
        client = MikroTikClient(switch_config)
        assert client.is_connected() is False

    @patch("app.services.mikrotik.connect")
    def test_connect_success(self, mock_connect, switch_config):
        """Test successful connection."""
        mock_api = MagicMock()
        mock_connect.return_value = mock_api

        client = MikroTikClient(switch_config)
        result = client.connect()

        assert result is True
        assert client.is_connected() is True
        mock_connect.assert_called_once_with(
            host=switch_config.host,
            username=switch_config.username,
            password=switch_config.password,
            port=switch_config.port,
        )

    @patch("app.services.mikrotik.connect")
    def test_connect_failure(self, mock_connect, switch_config):
        """Test failed connection."""
        mock_connect.side_effect = OSError("Connection refused")

        client = MikroTikClient(switch_config)
        result = client.connect()

        assert result is False
        assert client.is_connected() is False

    @patch("app.services.mikrotik.connect")
    def test_disconnect(self, mock_connect, switch_config):
        """Test disconnection."""
        mock_api = MagicMock()
        mock_connect.return_value = mock_api

        client = MikroTikClient(switch_config)
        client.connect()
        client.disconnect()

        assert client._api is None
        mock_api.close.assert_called_once()

    @patch("app.services.mikrotik.connect")
    def test_get_arp_table(self, mock_connect, switch_config):
        """Test getting ARP table."""
        mock_api = MagicMock()
        mock_connect.return_value = mock_api

        # Mock the path method to return ARP entries
        mock_api.path.return_value = [
            {"address": "192.168.1.100", "mac-address": "AA:BB:CC:DD:EE:01", "interface": "ether1"},
            {"address": "192.168.1.101", "mac-address": "AA:BB:CC:DD:EE:02", "interface": "ether2"},
        ]

        client = MikroTikClient(switch_config)
        client.connect()
        entries = client.get_arp_table()

        assert len(entries) == 2
        assert entries[0].ip == "192.168.1.100"
        assert entries[0].mac == "AA:BB:CC:DD:EE:01"

    @patch("app.services.mikrotik.connect")
    def test_get_bridge_hosts(self, mock_connect, switch_config):
        """Test getting bridge hosts."""
        mock_api = MagicMock()
        mock_connect.return_value = mock_api

        # Mock the path method to return bridge hosts
        mock_api.path.return_value = [
            {"mac-address": "AA:BB:CC:DD:EE:01", "on-interface": "ether1", "bridge": "bridge1"},
            {"mac-address": "AA:BB:CC:DD:EE:02", "on-interface": "ether2", "bridge": "bridge1"},
        ]

        client = MikroTikClient(switch_config)
        client.connect()
        hosts = client.get_bridge_hosts()

        assert len(hosts) == 2
        assert hosts[0].mac == "AA:BB:CC:DD:EE:01"
        assert hosts[0].interface == "ether1"


class TestDataClasses:
    """Test data classes."""

    def test_arp_entry(self):
        """Test ArpEntry creation."""
        entry = ArpEntry(ip="192.168.1.100", mac="AA:BB:CC:DD:EE:01", interface="ether1")
        assert entry.ip == "192.168.1.100"
        assert entry.mac == "AA:BB:CC:DD:EE:01"
        assert entry.interface == "ether1"

    def test_bridge_host(self):
        """Test BridgeHost creation."""
        host = BridgeHost(mac="AA:BB:CC:DD:EE:01", interface="ether1", bridge="bridge1")
        assert host.mac == "AA:BB:CC:DD:EE:01"
        assert host.interface == "ether1"
        assert host.bridge == "bridge1"

    def test_interface_info(self):
        """Test InterfaceInfo creation."""
        info = InterfaceInfo(
            name="ether1",
            type="ethernet",
            running=True,
            speed="1Gbps",
            rx_bytes=1000,
            tx_bytes=2000,
            rx_dropped=0,
            tx_dropped=0,
            rx_errors=0,
            tx_errors=0,
            rx_fcs_errors=0,
            tx_fcs_errors=0,
        )
        assert info.name == "ether1"
        assert info.running is True
        assert info.speed == "1Gbps"
