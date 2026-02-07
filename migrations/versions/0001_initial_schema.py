"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("imap_host", sa.String(255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("imap_user", sa.String(255), nullable=False),
        sa.Column("imap_password", sa.String(255), nullable=False),
        sa.Column("use_ssl", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_uid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("discord_webhook_url", sa.String(500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "rule_conditions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "rule_id",
            sa.Integer(),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", sa.String(20), nullable=False),
        sa.Column(
            "match_type",
            sa.String(20),
            nullable=False,
            server_default="contains",
        ),
        sa.Column("pattern", sa.String(500), nullable=False),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_table(
        "failure_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "rule_id",
            sa.Integer(),
            sa.ForeignKey("rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("message_uid", sa.Integer(), nullable=True),
        sa.Column("from_address", sa.String(500), nullable=True),
        sa.Column("subject", sa.String(1000), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "worker_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_running", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "poll_interval", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Insert default worker state row
    op.execute(
        "INSERT INTO worker_state (id, is_running, poll_interval) VALUES (1, true, 60)"
    )


def downgrade():
    op.drop_table("worker_state")
    op.drop_table("failure_logs")
    op.drop_table("rule_conditions")
    op.drop_table("rules")
    op.drop_table("accounts")
