"""add notification_formats table and notification_format_id to rules

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_notification_format"
down_revision = "0002_discord_webhooks_table"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create notification_formats table
    op.create_table(
        "notification_formats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # 2. Add notification_format_id to rules
    op.add_column(
        "rules",
        sa.Column(
            "notification_format_id",
            sa.Integer(),
            sa.ForeignKey("notification_formats.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # 3. Insert default format
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            INSERT INTO notification_formats (name, template)
            VALUES (:name, :template)
            RETURNING id
        """),
        {
            "name": "デフォルト",
            "template": "{\n  \"title\": \"📬 新着メール通知\",\n  \"color\": 5798242,\n  \"fields\": [\n    {\"name\": \"アカウント\", \"value\": \"{{ account_name }}\", \"inline\": true},\n    {\"name\": \"ルール\", \"value\": \"{{ rule_name }}\", \"inline\": true},\n    {\"name\": \"送信元\", \"value\": \"{{ from_address }}\", \"inline\": false},\n    {\"name\": \"件名\", \"value\": \"{{ subject }}\", \"inline\": false}\n  ]\n}\n"
        }
    )
    default_id = result.scalar()

    # 4. Set all existing rules to use default format
    conn.execute(
        sa.text("UPDATE rules SET notification_format_id = :id WHERE notification_format_id IS NULL"),
        {"id": default_id}
    )


def downgrade():
    op.drop_column("rules", "notification_format_id")
    op.drop_table("notification_formats")
