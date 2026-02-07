"""IMAP utility: fetch available mailbox names (folders) for an account."""

import imaplib
import logging
import imapclient

def list_mailboxes(host, port, user, password, use_ssl=True):
    """
    Fetch available mailbox names (folders) for an account.
    
    use_ssl=True:
      - If port is 993, use implicit SSL (IMAP4_SSL)
      - Otherwise (e.g., 1143 for Proton Bridge), use STARTTLS
    """
    try:
        if use_ssl:
            if port == 993:
                # Implicit SSL (standard IMAPS)
                conn = imaplib.IMAP4_SSL(host, port)
            else:
                # STARTTLS (e.g., Proton Bridge on port 1143)
                conn = imaplib.IMAP4(host, port)
                conn.starttls()
        else:
            conn = imaplib.IMAP4(host, port)
        conn.login(user, password)
        status, mailboxes = conn.list()
        conn.logout()
        if status != "OK":
            return []
        result = []
        for mbox in mailboxes:
            parts = mbox.decode().split(' "/" ')
            if len(parts) == 2:
                # decode IMAP modified UTF-7 to Unicode
                try:
                    decoded = imapclient.imap_utf7.decode(parts[1].strip('"'))
                except Exception:
                    decoded = parts[1].strip('"')
                result.append(decoded)
        return result
    except Exception as exc:
        logging.exception("IMAP list failed for %s@%s:%s", user, host, port)
        return []
