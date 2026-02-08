"""
Mail Notifier Worker Daemon
──────────────────────────
Periodically polls IMAP accounts using INTERNALDATE-based cursor (high-water mark),
evaluates rules in position order (first‑match‑wins), sends Discord notifications,
and logs failures. Controlled via the worker_state table (pause / resume / interval).

Deduplication: Uses Message-ID to avoid processing the same email multiple times
(important for Proton Mail Bridge where labels = folders).
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Ensure the project root is importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Account, Rule, FailureLog, WorkerState, WorkerTrigger
from app.imap_client import fetch_new_messages
from app.notify import evaluate_and_notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker")

# Default poll interval from env; overridden by DB value at runtime
DEFAULT_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))

# Maximum number of Message-IDs to keep for deduplication (FIFO)
MAX_MESSAGE_IDS = 1000


def cleanup_old_logs():
    """Remove failure logs older than 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    deleted = FailureLog.query.filter(FailureLog.created_at < cutoff).delete()
    if deleted:
        db.session.commit()
        logger.info("Cleaned up %d old failure log(s)", deleted)


def process_account(account: Account):
    """Fetch new mail for *account* and evaluate rules using INTERNALDATE cursor."""
    logger.info("Checking %s (%s@%s:%s)", account.name, account.imap_user, account.imap_host, account.imap_port)

    # Expire cached objects so we always read the latest notification formats
    db.session.expire_all()

    # Initialize cursor if this is the first run
    if account.last_processed_internal_date is None:
        # Set cursor to current time (don't process existing emails on first run)
        account.last_processed_internal_date = datetime.now(timezone.utc)
        db.session.commit()
        logger.info("初回実行: カーソルを現在時刻に初期化しました")
        return

    # Ensure cursor is timezone-aware (convert from DB if needed)
    cursor = account.last_processed_internal_date
    if cursor.tzinfo is None:
        cursor = cursor.replace(tzinfo=timezone.utc)
        logger.debug("Converted naive cursor to UTC-aware")

    # Load deduplication cache
    try:
        processed_ids = json.loads(account.processed_message_ids) if account.processed_message_ids else []
    except json.JSONDecodeError:
        processed_ids = []
        logger.warning("Message-ID cache parse error, resetting")

    try:
        messages = fetch_new_messages(
            host=account.imap_host,
            port=account.imap_port,
            user=account.imap_user,
            password=account.imap_password,
            use_ssl=account.use_ssl,
            last_processed_date=cursor,
            mailbox_name=account.mailbox_name,
            ssl_mode=getattr(account, 'ssl_mode', None),
        )
    except Exception as exc:
        log = FailureLog(
            account_id=account.id,
            error_message=f"IMAP error: {exc}",
        )
        db.session.add(log)
        db.session.commit()
        return

    max_internal_date = cursor
    processed_count = 0
    skipped_count = 0

    for msg in messages:
        # Deduplication: skip if Message-ID already processed
        if msg.message_id and msg.message_id in processed_ids:
            logger.debug("  Duplicate Message-ID %s, skipping", msg.message_id)
            skipped_count += 1
            continue

        logger.info("  New mail internal_date=%s from=%s subject=%s", 
                   msg.internal_date.isoformat(), msg.from_address, msg.subject)
        
        evaluate_and_notify(account, msg)
        processed_count += 1

        # Update high-water mark
        if msg.internal_date > max_internal_date:
            max_internal_date = msg.internal_date

        # Add to deduplication cache
        if msg.message_id:
            processed_ids.append(msg.message_id)

    if processed_count == 0 and skipped_count == 0:
        logger.debug("No new messages for %s", account.name)
        return

    # Trim deduplication cache (FIFO)
    if len(processed_ids) > MAX_MESSAGE_IDS:
        processed_ids = processed_ids[-MAX_MESSAGE_IDS:]

    # Update cursor and cache
    if max_internal_date > cursor:
        account.last_processed_internal_date = max_internal_date
        account.processed_message_ids = json.dumps(processed_ids)
        db.session.commit()
        logger.info("Cursor updated to %s (%d processed, %d skipped)", 
                   max_internal_date.isoformat(), processed_count, skipped_count)
    elif processed_ids:
        # Update cache even if cursor didn't move
        account.processed_message_ids = json.dumps(processed_ids)
        db.session.commit()


def run():
    """Main daemon loop."""
    app = create_app()

    with app.app_context():
        logger.info("Worker started – default interval %ds", DEFAULT_INTERVAL)

        while True:
            # Read worker state from DB (SQLAlchemy 2.x compatible)
            state = db.session.get(WorkerState, 1)
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

            # Check for triggered accounts (immediate polling requests)
            triggers = WorkerTrigger.query.all()
            triggered_account_ids = {t.account_id for t in triggers}
            
            if triggers:
                logger.info("Processing %d triggered account(s)", len(triggers))
                for trigger in triggers:
                    account = Account.query.get(trigger.account_id)
                    if account and account.enabled:
                        try:
                            logger.info("Triggered polling for %s", account.name)
                            process_account(account)
                        except Exception:
                            logger.exception("Error processing triggered account %s", account.name)
                
                # Delete all processed triggers
                for trigger in triggers:
                    db.session.delete(trigger)
                db.session.commit()

            # Load active accounts (excluding already triggered ones)
            accounts = Account.query.filter_by(enabled=True).all()

            for account in accounts:
                if account.id in triggered_account_ids:
                    # Already processed in this cycle
                    continue
                try:
                    process_account(account)
                except Exception:
                    logger.exception("Unhandled error processing %s", account.name)

            logger.debug("Cycle complete – sleeping %ds", interval)
            time.sleep(interval)


if __name__ == "__main__":
    run()
