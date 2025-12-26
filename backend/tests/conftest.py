import os
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create switches.yaml
        switches_data = {
            "switches": [
                {
                    "name": "test-switch-1",
                    "host": "192.168.1.1",
                    "username": "admin",
                    "password": "admin",
                    "port": 8728,
                },
                {
                    "name": "test-switch-2",
                    "host": "192.168.1.2",
                    "username": "admin",
                    "password": "admin",
                    "port": 8728,
                },
            ]
        }
        with open(Path(tmpdir) / "switches.yaml", "w") as f:
            yaml.dump(switches_data, f)

        # Create devices.yaml
        devices_data = {
            "devices": [
                {
                    "name": "Server-01",
                    "ip": "192.168.1.100",
                    "expected_speed": "1Gbps",
                },
                {
                    "name": "Workstation-01",
                    "ip": "192.168.1.101",
                    "expected_speed": "1Gbps",
                },
                {
                    "name": "IoT-Device-01",
                    "ip": "192.168.1.102",
                    "expected_speed": "100Mbps",
                },
            ]
        }
        with open(Path(tmpdir) / "devices.yaml", "w") as f:
            yaml.dump(devices_data, f)

        yield tmpdir


@pytest.fixture
def test_client(temp_config_dir, monkeypatch):
    """Create a test client with mocked config."""
    monkeypatch.setenv("NLNS_CONFIG_DIR", temp_config_dir)

    # Import after setting environment variable
    from app.main import app
    from app.services.monitor import monitor

    # Reset monitor state
    monitor._switches = []
    monitor._devices = []
    monitor._device_statuses = {}
    monitor._port_errors = []
    monitor._switch_statuses = {}

    with TestClient(app) as client:
        yield client
