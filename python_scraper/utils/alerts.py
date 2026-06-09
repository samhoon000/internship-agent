import os
import json
import logging
import urllib.request
from datetime import datetime

logger = logging.getLogger("python_scraper.utils.alerts")

# Throttle cache to avoid spamming alerts in Python if called repeatedly
_last_alerts = {}
THROTTLE_WINDOW_SEC = 60

def send_discord_alert(title: str, description: str, status: str = 'error'):
    """
    Sends a structured rich embed alert to Discord Webhook.
    Throttles duplicate alerts within a 1-minute window.
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning(f"[Alerting] DISCORD_WEBHOOK_URL not set. Skipping alert: {title}")
        return

    # Throttling check
    now = datetime.utcnow().timestamp()
    last_time = _last_alerts.get(title, 0)
    if now - last_time < THROTTLE_WINDOW_SEC:
        logger.debug(f"[Alerting] Throttling alert: '{title}' (sent {int(now - last_time)}s ago)")
        return
    _last_alerts[title] = now

    # Map status to decimal color
    color = 16711680  # Red
    if status == 'warning':
        color = 16776960  # Yellow
    elif status == 'success':
        color = 65280  # Green
    elif status == 'info':
        color = 255  # Blue

    payload = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {
                    "text": "Internship Aggregator Python Scraper"
                }
            }
        ]
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            if response.status not in (200, 204):
                logger.error(f"[Alerting] Discord webhook returned status code {response.status}")
    except Exception as e:
        logger.error(f"[Alerting] Failed to dispatch Discord alert: {e}", exc_info=True)
