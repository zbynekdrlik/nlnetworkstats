import os
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings

from app.models import DeviceConfig, SwitchConfig


class Settings(BaseSettings):
    config_dir: str = "/app/config"
    poll_interval: int = 10  # seconds - fast polling for production
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_prefix = "NLNS_"


settings = Settings()


def get_config_path() -> Path:
    """Get the configuration directory path."""
    config_dir = os.environ.get("NLNS_CONFIG_DIR", settings.config_dir)
    return Path(config_dir)


def load_switches() -> list[SwitchConfig]:
    """Load switch configurations from YAML file."""
    config_path = get_config_path() / "switches.yaml"
    if not config_path.exists():
        return []

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data or "switches" not in data:
        return []

    return [SwitchConfig(**switch) for switch in data["switches"]]


def load_devices() -> list[DeviceConfig]:
    """Load device configurations from YAML file."""
    config_path = get_config_path() / "devices.yaml"
    if not config_path.exists():
        return []

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data or "devices" not in data:
        return []

    return [DeviceConfig(**device) for device in data["devices"]]
