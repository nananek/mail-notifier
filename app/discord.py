"""Discord webhook delivery."""

import logging
import requests

logger = logging.getLogger(__name__)

TIMEOUT = 10  # seconds


def send_notification(
    webhook_url: str,
    *,
    account_name: str,
    from_address: str,
    subject: str,
    rule_name: str,
) -> None:
    """
    Post a rich embed to a Discord webhook.
    Raises on HTTP errors so the caller can log failures.
    """
    embed = {
        "title": "📬 新着メール通知",
        "color": 0x5865F2,  # Discord blurple
        "fields": [
            {"name": "アカウント", "value": account_name, "inline": True},
            {"name": "ルール", "value": rule_name, "inline": True},
            {"name": "送信元", "value": from_address, "inline": False},
            {"name": "件名", "value": subject, "inline": False},
        ],
    }

    payload = {"embeds": [embed]}

    resp = requests.post(webhook_url, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    logger.info("Discord notification sent for rule=%s subject=%s", rule_name, subject)
