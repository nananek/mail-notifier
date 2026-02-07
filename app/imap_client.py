"""IMAP helper – fetch new messages from a mailbox."""

import email
import email.header
import imaplib
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class MailMessage:
    uid: int
    from_address: str
    subject: str


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


def fetch_new_messages(
    host: str,
    port: int,
    user: str,
    password: str,
    use_ssl: bool,
    last_uid: int,
) -> List[MailMessage]:
    """
    Connect via IMAP, search for messages with UID > last_uid in INBOX,
    and return a list of MailMessage objects.
    """
    messages: List[MailMessage] = []

    try:
        if use_ssl:
            conn = imaplib.IMAP4_SSL(host, port)
        else:
            conn = imaplib.IMAP4(host, port)

        conn.login(user, password)
        conn.select("INBOX", readonly=True)

        # Search for UIDs greater than last_uid
        search_criterion = f"UID {last_uid + 1}:*"
        status, data = conn.uid("search", None, search_criterion)

        if status != "OK" or not data[0]:
            conn.close()
            conn.logout()
            return messages

        uid_list = data[0].split()

        for uid_bytes in uid_list:
            uid = int(uid_bytes)
            if uid <= last_uid:
                continue

            status, msg_data = conn.uid("fetch", uid_bytes, "(RFC822.HEADER)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw_header = msg_data[0][1]
            msg = email.message_from_bytes(raw_header)

            from_addr = decode_header_value(msg.get("From", ""))
            subj = decode_header_value(msg.get("Subject", ""))

            messages.append(MailMessage(uid=uid, from_address=from_addr, subject=subj))

        conn.close()
        conn.logout()

    except Exception:
        logger.exception("IMAP fetch failed for %s@%s:%s", user, host, port)
        raise

    return messages
