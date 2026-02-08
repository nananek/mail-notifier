from datetime import datetime, timezone

from app.extensions import db


class Account(db.Model):
    """IMAP mail account (Proton Mail Bridge / Gmail)."""

    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    imap_host = db.Column(db.String(255), nullable=False)
    imap_port = db.Column(db.Integer, nullable=False, default=993)
    imap_user = db.Column(db.String(255), nullable=False)
    imap_password = db.Column(db.String(255), nullable=False)
    use_ssl = db.Column(db.Boolean, nullable=False, default=True)
    ssl_mode = db.Column(db.String(20), nullable=False, default="ssl")  # "none", "starttls", "ssl"
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_uid = db.Column(db.Integer, nullable=False, default=0)  # Deprecated: use last_processed_internal_date instead
    mailbox_name = db.Column(db.String(120), nullable=False, default="INBOX")
    last_processed_internal_date = db.Column(db.DateTime, nullable=True)  # High-water mark for INTERNALDATE-based polling
    processed_message_ids = db.Column(db.Text, nullable=False, default="")  # JSON array of Message-IDs for deduplication
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Account {self.name}>"


class DiscordWebhook(db.Model):
    """Discord webhook destination."""

    __tablename__ = "discord_webhooks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    rules = db.relationship("Rule", back_populates="webhook")

    def __repr__(self):
        return f"<DiscordWebhook {self.name}>"



class NotificationFormat(db.Model):
    """Notification format for Discord messages."""
    __tablename__ = "notification_formats"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    template = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    rules = db.relationship("Rule", back_populates="notification_format")

    def __repr__(self):
        return f"<NotificationFormat {self.name}>"


class Rule(db.Model):
    """Notification rule – evaluated in `position` order; first match wins."""

    __tablename__ = "rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    discord_webhook_id = db.Column(
        db.Integer,
        db.ForeignKey("discord_webhooks.id", ondelete="SET NULL"),
        nullable=True,
    )
    notification_format_id = db.Column(
        db.Integer,
        db.ForeignKey("notification_formats.id", ondelete="SET NULL"),
        nullable=True,
    )
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    position = db.Column(db.Integer, nullable=False, default=0)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    webhook = db.relationship("DiscordWebhook", back_populates="rules")
    notification_format = db.relationship("NotificationFormat", back_populates="rules")
    account = db.relationship("Account")
    conditions = db.relationship(
        "RuleCondition", back_populates="rule", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Rule {self.name} @{self.position}>"


class RuleCondition(db.Model):
    """A single match clause belonging to a Rule (AND‑combined)."""

    __tablename__ = "rule_conditions"

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(
        db.Integer, db.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False
    )

    # Which field to match
    FIELD_FROM = "from"
    FIELD_TO = "to"
    FIELD_SUBJECT = "subject"
    FIELD_CHOICES = [FIELD_FROM, FIELD_TO, FIELD_SUBJECT]

    field = db.Column(db.String(20), nullable=False)

    # How to match
    MATCH_PREFIX = "prefix"
    MATCH_SUFFIX = "suffix"
    MATCH_CONTAINS = "contains"
    MATCH_REGEX = "regex"
    MATCH_CHOICES = [MATCH_PREFIX, MATCH_SUFFIX, MATCH_CONTAINS, MATCH_REGEX]

    match_type = db.Column(db.String(20), nullable=False, default=MATCH_CONTAINS)
    pattern = db.Column(db.String(500), nullable=False)

    rule = db.relationship("Rule", back_populates="conditions")

    def __repr__(self):
        return f"<RuleCondition {self.field} {self.match_type} '{self.pattern}'>"


class FailureLog(db.Model):
    """Records of failed Discord webhook deliveries (kept 30 days)."""

    __tablename__ = "failure_logs"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    rule_id = db.Column(
        db.Integer, db.ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    message_uid = db.Column(db.Integer, nullable=True)
    from_address = db.Column(db.String(500), nullable=True)
    subject = db.Column(db.String(1000), nullable=True)
    error_message = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    account = db.relationship("Account")
    rule = db.relationship("Rule")

    def __repr__(self):
        return f"<FailureLog {self.id} @ {self.created_at}>"


class WorkerState(db.Model):
    """Singleton row to control the worker daemon from the Web UI."""

    __tablename__ = "worker_state"

    id = db.Column(db.Integer, primary_key=True, default=1)
    is_running = db.Column(db.Boolean, nullable=False, default=True)
    poll_interval = db.Column(db.Integer, nullable=False, default=60)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WorkerTrigger(db.Model):
    """Trigger record to request immediate polling for a specific account."""

    __tablename__ = "worker_triggers"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    requested_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    account = db.relationship("Account")

    def __repr__(self):
        return f"<WorkerTrigger account_id={self.account_id} @ {self.requested_at}>"
