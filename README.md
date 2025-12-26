# NLNetworkStats

Network monitoring application for MikroTik switches. Monitors link speeds, compares against expected values, and displays port errors.

## Features

- Connect to MikroTik switches via RouterOS API
- Monitor device link speeds and compare with expected values
- Detect dropped, corrupted, and FCS error frames
- Web dashboard with auto-refresh
- Docker deployment

## Quick Start

### 1. Configure Switches

Edit `backend/config/switches.yaml`:

```yaml
switches:
  - name: switch-1
    host: 10.77.8.1
    username: admin
    password: admin
    port: 8728
```

### 2. Configure Devices

Edit `backend/config/devices.yaml`:

```yaml
devices:
  - name: "Server-01"
    ip: "10.77.8.100"
    expected_speed: "1Gbps"
  - name: "Workstation-05"
    ip: "10.77.9.50"
    expected_speed: "1Gbps"
```

### 3. Run with Docker

```bash
docker compose up -d
```

Access the dashboard at http://localhost:7777

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest  # run tests
uvicorn app.main:app --reload  # run dev server
```

### Frontend

```bash
cd frontend
npm install
npm test  # run tests
npm run dev  # run dev server on port 7777
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| GET | /api/status | System status |
| GET | /api/devices | All devices |
| GET | /api/devices/mismatched | Devices with speed mismatch |
| GET | /api/ports | All ports |
| GET | /api/ports/errors | Ports with errors |
| GET | /api/switches | Switch connection status |
| POST | /api/refresh | Force data refresh |

## License

MIT
