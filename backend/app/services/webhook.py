import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WEBHOOK_URL = "https://n8n-wh.newlevel.media/webhook/6fbb57fd-7347-4e35-8f18-d3648b5e3275"


async def send_webhook(event_type: str, data: dict[str, Any]) -> bool:
    """Send webhook notification with event data."""
    payload = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(WEBHOOK_URL, json=payload)
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook sent successfully: {event_type}")
                return True
            else:
                logger.warning(f"Webhook returned status {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send webhook: {e}")
        return False


def send_webhook_sync(event_type: str, data: dict[str, Any]) -> bool:
    """Send webhook notification synchronously."""
    payload = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(WEBHOOK_URL, json=payload)
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook sent successfully: {event_type}")
                return True
            else:
                logger.warning(f"Webhook returned status {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send webhook: {e}")
        return False
