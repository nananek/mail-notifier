"""Discord webhook delivery."""

import logging
import requests

logger = logging.getLogger(__name__)

TIMEOUT = 10  # seconds


def send_notification(
    webhook_url: str,
    *,
    rendered_message: str,
    rule_name: str = "",
    subject: str = "",
) -> None:
    """
    Post a rich embed to a Discord webhook.
    Raises on HTTP errors so the caller can log failures.
    """
    embed = {
        "title": "📬 新着メール通知",
        "color": 0x5865F2,
        "description": rendered_message,
    }
    payload = {"embeds": [embed]}
    resp = requests.post(webhook_url, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    logger.info("Discord notification sent for rule=%s subject=%s", rule_name, subject)
