"""
Shared notification logic – evaluate rules against a message and send Discord notifications.
Used by both the worker daemon and the "receive now" web route.
"""

import logging

from app.extensions import db
from app.models import Rule, FailureLog
from app.matcher import evaluate_rule
from app.discord import send_notification

logger = logging.getLogger(__name__)


def evaluate_and_notify(account, msg):
    """
    Evaluate all enabled rules against a single message and send a
    Discord notification for the first matching rule.

    Returns True if a rule matched and notification was attempted.
    """
    rules = Rule.query.order_by(Rule.position).all()

    for rule in rules:
        if not rule.enabled:
            continue

        # Check if rule is restricted to a specific account
        if rule.account_id is not None and rule.account_id != account.id:
            logger.debug("Rule '%s' skipped: account filter (%d != %d)", rule.name, rule.account_id, account.id)
            continue

        matched = evaluate_rule(
            rule,
            from_address=msg.from_address,
            to_address=msg.to_address,
            subject=msg.subject,
            account_id=account.id,
            account_name=account.name,
        )

        if not matched:
            continue

        if not rule.webhook:
            logger.warning("Rule '%s' matched but has no webhook configured", rule.name)
            return False

        logger.info("Matched rule '%s' → sending to Discord via '%s'", rule.name, rule.webhook.name)

        # Render notification message
        fmt = rule.notification_format
        if fmt and fmt.template:
            template_vars = {
                "account_name": account.name,
                "from_address": msg.from_address,
                "subject": msg.subject,
                "rule_name": rule.name,
                "date": msg.date,
            }
            try:
                rendered = fmt.template.format(**template_vars)
            except Exception as exc:
                logger.error("Format rendering failed: %s", exc)
                rendered = (
                    f"**アカウント:** {account.name}\n"
                    f"**ルール:** {rule.name}\n"
                    f"**送信元:** {msg.from_address}\n"
                    f"**件名:** {msg.subject}"
                )
        else:
            rendered = (
                f"**アカウント:** {account.name}\n"
                f"**ルール:** {rule.name}\n"
                f"**送信元:** {msg.from_address}\n"
                f"**件名:** {msg.subject}"
            )

        # Send to Discord
        try:
            send_notification(
                rule.webhook.url,
                rendered_message=rendered,
                rule_name=rule.name,
                subject=msg.subject,
            )
        except Exception as exc:
            logger.error("Discord send failed: %s", exc)
            log = FailureLog(
                account_id=account.id,
                rule_id=rule.id,
                message_uid=msg.uid,
                from_address=msg.from_address,
                subject=msg.subject,
                error_message=f"Discord error: {exc}",
            )
            db.session.add(log)
            db.session.commit()

        return True  # first match wins

    return False
