"""IMAP utility: fetch available mailbox names (folders) for an account."""

import imaplib
import logging
import imapclient

def list_mailboxes(host, port, user, password, use_ssl=True, ssl_mode=None):
    """
    Fetch available mailbox names (folders) for an account.
    
    ssl_mode: "none", "starttls", or "ssl" (if None, falls back to use_ssl+port logic)
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
