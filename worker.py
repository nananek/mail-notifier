"""
Mail Notifier Worker Daemon
──────────────────────────
Periodically polls IMAP accounts, evaluates rules in position order
(first‑match‑wins), sends Discord notifications, and logs failures.
Controlled via the worker_state table (pause / resume / interval).
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Ensure the project root is importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Account, Rule, FailureLog, WorkerState
from app.imap_client import fetch_new_messages
from app.matcher import evaluate_rule
from app.discord import send_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker")

# Default poll interval from env; overridden by DB value at runtime
DEFAULT_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))


def cleanup_old_logs():
    """Remove failure logs older than 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    deleted = FailureLog.query.filter(FailureLog.created_at < cutoff).delete()
    if deleted:
        db.session.commit()
        logger.info("Cleaned up %d old failure log(s)", deleted)


def process_account(account: Account, rules):
    """Fetch new mail for *account* and evaluate rules."""
    logger.info("Checking %s (%s@%s:%s)", account.name, account.imap_user, account.imap_host, account.imap_port)

    try:
        messages = fetch_new_messages(
            host=account.imap_host,
            port=account.imap_port,
            user=account.imap_user,
            password=account.imap_password,
            use_ssl=account.use_ssl,
            last_uid=account.last_uid,
        )
    except Exception as exc:
        log = FailureLog(
            account_id=account.id,
            error_message=f"IMAP error: {exc}",
        )
        db.session.add(log)
        db.session.commit()
        return

    if not messages:
        logger.debug("No new messages for %s", account.name)
        return

    max_uid = account.last_uid

    for msg in messages:
        logger.info("  New mail uid=%d from=%s subject=%s", msg.uid, msg.from_address, msg.subject)

        # Evaluate rules in position order – first match wins
        for rule in rules:
            if not rule.enabled:
                continue
            matched = evaluate_rule(
                rule,
                from_address=msg.from_address,
                subject=msg.subject,
                account_id=account.id,
                account_name=account.name,
            )
            if matched:
                logger.info("  Matched rule '%s' → sending to Discord", rule.name)
                try:
                    send_notification(
                        rule.discord_webhook_url,
                        account_name=account.name,
                        from_address=msg.from_address,
                        subject=msg.subject,
                        rule_name=rule.name,
                    )
                except Exception as exc:
                    logger.error("  Discord send failed: %s", exc)
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
                break  # first match wins

        if msg.uid > max_uid:
            max_uid = msg.uid

    # Persist the high‑water‑mark UID
    if max_uid > account.last_uid:
        account.last_uid = max_uid
        db.session.commit()


def run():
    """Main daemon loop."""
    app = create_app()

    with app.app_context():
        logger.info("Worker started – default interval %ds", DEFAULT_INTERVAL)

        while True:
            # Read worker state from DB
            state = WorkerState.query.get(1)
            if state is None:
                state = WorkerState(id=1, is_running=True, poll_interval=DEFAULT_INTERVAL)
                db.session.add(state)
                db.session.commit()

            interval = state.poll_interval or DEFAULT_INTERVAL

            if not state.is_running:
                logger.debug("Worker paused – sleeping %ds", interval)
                time.sleep(interval)
                continue

            # Periodic log cleanup
            cleanup_old_logs()

            # Load active accounts & rules
            accounts = Account.query.filter_by(enabled=True).all()
            rules = Rule.query.order_by(Rule.position).all()

            for account in accounts:
                try:
                    process_account(account, rules)
                except Exception:
                    logger.exception("Unhandled error processing %s", account.name)

            logger.debug("Cycle complete – sleeping %ds", interval)
            time.sleep(interval)


if __name__ == "__main__":
    run()
