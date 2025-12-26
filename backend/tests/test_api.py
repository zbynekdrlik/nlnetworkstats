import pytest


def test_health_check(test_client):
    """Test health check endpoint."""
    response = test_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint(test_client):
    """Test root endpoint."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "NLNetworkStats"
    assert "version" in data


def test_get_system_status(test_client):
    """Test getting system status."""
    response = test_client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_devices" in data
    assert "online_devices" in data
    assert "mismatched_speeds" in data
    assert "ports_with_errors" in data


def test_get_switches(test_client):
    """Test getting switch statuses."""
    response = test_client.get("/api/switches")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_devices(test_client):
    """Test getting device statuses."""
    response = test_client.get("/api/devices")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_mismatched_devices(test_client):
    """Test getting mismatched devices."""
    response = test_client.get("/api/devices/mismatched")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_ports(test_client):
    """Test getting port statistics."""
    response = test_client.get("/api/ports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_ports_with_errors(test_client):
    """Test getting ports with errors."""
    response = test_client.get("/api/ports/errors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
