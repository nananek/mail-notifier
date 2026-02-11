"""POP3 helper – fetch new messages using UIDL + Date-based cursor."""

import email
import logging
import poplib
from typing import Iterator, Optional, Set
from datetime import datetime, timezone

from app.imap_client import MailMessage, decode_header_value, parse_internal_date

logger = logging.getLogger(__name__)


def fetch_new_messages(
    host: str,
    port: int,
    user: str,
    password: str,
    use_ssl: bool,
    last_processed_date: Optional[datetime] = None,
    mailbox_name: str = "INBOX",  # ignored for POP3
    ssl_mode: str = None,
    processed_uidls: Optional[Set[str]] = None,
) -> Iterator[MailMessage]:
    """
    Connect via POP3 and fetch new messages using UIDL + Date-based cursor.

    Algorithm:
    1. Connect and authenticate
    2. UIDL to get message-number -> UIDL mapping
    3. Skip messages whose UIDL (or synthetic Message-ID) is in processed_uidls
    4. For remaining: TOP to fetch headers only
    5. Parse Date header; client-side filter: only yield if date > last_processed_date
    6. Return MailMessage objects sorted by date

    Args:
        last_processed_date: High-water mark (UTC datetime). If None, initialization mode.
        mailbox_name: Ignored for POP3 (always INBOX).
        ssl_mode: "none", "starttls", or "ssl".
        processed_uidls: Set of already-processed identifiers for fast lookup.
    """
    if processed_uidls is None:
        processed_uidls = set()

    try:
        # Establish connection
        if ssl_mode:
            if ssl_mode == "ssl":
                conn = poplib.POP3_SSL(host, port)
            elif ssl_mode == "starttls":
                conn = poplib.POP3(host, port)
                conn.stls()
            else:  # "none"
                conn = poplib.POP3(host, port)
        else:
            # Legacy: use_ssl + port-based logic
            if use_ssl:
                if port == 995:
                    conn = poplib.POP3_SSL(host, port)
                else:
                    conn = poplib.POP3(host, port)
                    conn.stls()
            else:
                conn = poplib.POP3(host, port)

        conn.user(user)
        conn.pass_(password)

        # Initialization mode: don't fetch anything on first run
        if last_processed_date is None:
            logger.info("POP3 初回実行モード: メールを取得しません（カーソルを初期化してください）")
            conn.quit()
            return iter([])

        # Get UIDL listing
        resp, uidl_list, _ = conn.uidl()
        if not uidl_list:
            conn.quit()
            return iter([])

        # Parse UIDL list: each entry is b"msg_num uidl"
        msg_uidls = []
        for entry in uidl_list:
            line = entry.decode("utf-8", errors="replace") if isinstance(entry, bytes) else entry
            parts = line.split(None, 1)
            if len(parts) == 2:
                msg_uidls.append((int(parts[0]), parts[1]))

        # Filter out already-processed UIDLs
        new_msgs = []
        for num, uidl in msg_uidls:
            if uidl in processed_uidls or f"<pop3-uidl-{uidl}>" in processed_uidls:
                continue
            new_msgs.append((num, uidl))

        if not new_msgs:
            logger.debug("POP3: no new UIDLs found")
            conn.quit()
            return iter([])

        logger.debug("POP3: %d new UIDL(s) out of %d total", len(new_msgs), len(msg_uidls))

        messages = []
        for msg_num, uidl in new_msgs:
            try:
                # TOP msg_num 0 -> fetch headers only (0 body lines)
                resp, header_lines, _ = conn.top(msg_num, 0)
            except poplib.error_proto as exc:
                logger.warning("POP3 TOP failed for msg %d (UIDL %s): %s", msg_num, uidl, exc)
                continue

            raw_header = b"\r\n".join(header_lines)
            msg = email.message_from_bytes(raw_header)

            # Parse Date header as the "internal date" equivalent
            date_header = msg.get("Date", "")
            if not date_header:
                logger.warning("POP3 msg %d (UIDL %s): no Date header, skipping", msg_num, uidl)
                continue

            msg_date = parse_internal_date(date_header)

            # Client-side date filter
            if msg_date <= last_processed_date:
                logger.debug("POP3 msg %d: date %s <= cursor, skipping", msg_num, msg_date.isoformat())
                continue

            from_addr = decode_header_value(msg.get("From", ""))
            to_addr = decode_header_value(msg.get("To", ""))
            subj = decode_header_value(msg.get("Subject", ""))
            message_id = msg.get("Message-ID", "").strip()

            # Use UIDL as fallback if no Message-ID header
            if not message_id:
                message_id = f"<pop3-uidl-{uidl}>"
                logger.debug("POP3 msg %d: no Message-ID, using UIDL-based ID: %s", msg_num, message_id)

            messages.append(MailMessage(
                uid=msg_num,
                from_address=from_addr,
                to_address=to_addr,
                subject=subj,
                date=date_header,
                message_id=message_id,
                internal_date=msg_date,
            ))

        conn.quit()

        # Sort by date for chronological processing
        messages.sort(key=lambda m: m.internal_date)

        logger.info("POP3: found %d new message(s) after %s", len(messages), last_processed_date.isoformat())
        return iter(messages)

    except Exception:
        logger.exception("POP3 fetch failed for %s@%s:%s", user, host, port)
        raise
