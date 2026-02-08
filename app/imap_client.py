"""IMAP helper – fetch new messages from a mailbox using INTERNALDATE-based cursor."""

import email
import email.header
import email.utils
import imaplib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class MailMessage:
    uid: int
    from_address: str
    to_address: str
    subject: str
    date: str
    message_id: str
    internal_date: datetime  # INTERNALDATE from IMAP server (UTC)


def decode_header_value(raw: str) -> str:
    """Decode an RFC‑2047 encoded header into a plain string."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return "".join(decoded)


def parse_internal_date(date_str: str) -> datetime:
    """
    Parse IMAP INTERNALDATE string to UTC datetime.
    Format: "DD-Mon-YYYY HH:MM:SS +HHMM"
    Example: "08-Feb-2026 12:34:56 +0000"
    """
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        # Convert to UTC
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        logger.warning("Failed to parse INTERNALDATE '%s': %s", date_str, exc)
        # Fallback: use current time
        return datetime.now(timezone.utc)


def fetch_new_messages(
    host: str,
    port: int,
    user: str,
    password: str,
    use_ssl: bool,
    last_processed_date: Optional[datetime] = None,
    mailbox_name: str = "INBOX",
    ssl_mode: str = None,
) -> Iterator[MailMessage]:
    """
    Connect via IMAP and fetch messages using INTERNALDATE-based cursor.
    
    Logic:
    1. Search for messages since (last_processed_date - 1 day) to account for timezone drift
    2. Fetch INTERNALDATE and headers for each message
    3. Client-side filter: only yield messages with internal_date > last_processed_date
    
    Args:
        last_processed_date: High-water mark (UTC datetime). If None, fetches nothing (initialization mode).
        ssl_mode: "none", "starttls", or "ssl"
    
    Returns:
        Iterator of MailMessage objects sorted by INTERNALDATE
    """
    try:
        # Determine connection mode
        if ssl_mode:
            if ssl_mode == "ssl":
                conn = imaplib.IMAP4_SSL(host, port)
            elif ssl_mode == "starttls":
                conn = imaplib.IMAP4(host, port)
                conn.starttls()
            else:  # "none"
                conn = imaplib.IMAP4(host, port)
        else:
            # Legacy: use_ssl + port-based logic
            if use_ssl:
                if port == 993:
                    conn = imaplib.IMAP4_SSL(host, port)
                else:
                    conn = imaplib.IMAP4(host, port)
                    conn.starttls()
            else:
                conn = imaplib.IMAP4(host, port)

        conn.login(user, password)
        status, _ = conn.select(mailbox_name, readonly=True)
        if status != "OK":
            raise RuntimeError(f"IMAPフォルダ選択に失敗しました: {mailbox_name}")

        # Initialization mode: don't fetch anything on first run
        if last_processed_date is None:
            logger.info("初回実行モード: メールを取得しません（カーソルを初期化してください）")
            conn.close()
            conn.logout()
            return iter([])

        # Calculate search date: 1 day before last_processed_date to handle timezone drift
        search_date = (last_processed_date - timedelta(days=1)).date()
        search_criterion = search_date.strftime("%d-%b-%Y")
        
        logger.debug("Searching messages SINCE %s (last_processed: %s)", search_criterion, last_processed_date.isoformat())
        
        status, data = conn.uid("search", None, f"SINCE {search_criterion}")

        if status != "OK" or not data[0]:
            conn.close()
            conn.logout()
            return iter([])

        uid_list = data[0].split()
        messages = []

        for uid_bytes in uid_list:
            uid = int(uid_bytes)

            # Fetch INTERNALDATE and headers
            status, msg_data = conn.uid("fetch", uid_bytes, "(INTERNALDATE RFC822.HEADER)")
            if status != "OK" or not msg_data or not msg_data[0]:
                logger.warning("UID %d: fetch failed or empty response", uid)
                continue

            # Debug: log the raw response structure
            logger.debug("UID %d: msg_data type=%s, len=%d", uid, type(msg_data), len(msg_data))
            if msg_data and len(msg_data) > 0:
                logger.debug("UID %d: msg_data[0] type=%s", uid, type(msg_data[0]))

            # Parse INTERNALDATE from response
            # msg_data structure varies by server:
            # Gmail: [(b'123 (RFC822.HEADER {size}', b'header data'), b')']
            # Others: [(b'123 (INTERNALDATE "..." RFC822.HEADER {size}', b'header data')]
            internal_date_str = None
            raw_header = None
            
            # Extract from first element (which is usually a tuple)
            first_elem = msg_data[0]
            if isinstance(first_elem, tuple) and len(first_elem) >= 2:
                # Standard format: (metadata_bytes, header_bytes)
                metadata = first_elem[0]
                raw_header = first_elem[1]
                
                if isinstance(metadata, bytes):
                    metadata_str = metadata.decode('utf-8', errors='ignore')
                    logger.debug("UID %d: metadata=%s", uid, metadata_str[:200])
                    import re
                    match = re.search(r'INTERNALDATE "([^"]+)"', metadata_str)
                    if match:
                        internal_date_str = match.group(1)
            elif isinstance(first_elem, bytes):
                # Fallback: try to parse from bytes directly
                metadata_str = first_elem.decode('utf-8', errors='ignore')
                logger.debug("UID %d: metadata (bytes)=%s", uid, metadata_str[:200])
                import re
                match = re.search(r'INTERNALDATE "([^"]+)"', metadata_str)
                if match:
                    internal_date_str = match.group(1)
                # Try to get header from next element
                if len(msg_data) > 1 and isinstance(msg_data[1], bytes):
                    raw_header = msg_data[1]
            
            if not raw_header:
                logger.warning("UID %d: header data not found in response", uid)
                continue
            
            # Parse message headers first
            msg = email.message_from_bytes(raw_header)
            
            # If INTERNALDATE not found, fall back to Date header
            if not internal_date_str:
                date_header = msg.get("Date", "")
                logger.debug("UID %d: INTERNALDATE not found, using Date header: %s", uid, date_header)
                if date_header:
                    internal_date_str = date_header
                else:
                    logger.warning("UID %d: Neither INTERNALDATE nor Date header found, skipping", uid)
                    continue
            
            internal_date = parse_internal_date(internal_date_str)
            
            # Client-side filter: skip if not newer than cursor
            if internal_date <= last_processed_date:
                logger.debug("UID %d: internal_date %s <= cursor, skipping", uid, internal_date.isoformat())
                continue

            from_addr = decode_header_value(msg.get("From", ""))
            to_addr = decode_header_value(msg.get("To", ""))
            subj = decode_header_value(msg.get("Subject", ""))
            date_str = msg.get("Date", "")
            message_id = msg.get("Message-ID", "").strip()

            messages.append(MailMessage(
                uid=uid,
                from_address=from_addr,
                to_address=to_addr,
                subject=subj,
                date=date_str,
                message_id=message_id,
                internal_date=internal_date,
            ))

        conn.close()
        conn.logout()

        # Sort by INTERNALDATE to ensure chronological processing
        messages.sort(key=lambda m: m.internal_date)
        
        logger.info("Found %d new message(s) after %s", len(messages), last_processed_date.isoformat())
        return iter(messages)

    except Exception:
        logger.exception("IMAP fetch failed for %s@%s:%s", user, host, port)
        raise
