"""add discord_webhooks table, migrate data from rules

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_discord_webhooks_table"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create discord_webhooks table
    op.create_table(
        "discord_webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
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

    # 2. Add discord_webhook_id column to rules (nullable for now)
    op.add_column(
        "rules",
        sa.Column(
            "discord_webhook_id",
            sa.Integer(),
            sa.ForeignKey("discord_webhooks.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # 3. Migrate existing webhook URLs into the new table
    #    Use raw SQL to handle the data migration
    conn = op.get_bind()

    # Get distinct webhook URLs from existing rules
    rows = conn.execute(
        sa.text("SELECT DISTINCT discord_webhook_url FROM rules WHERE discord_webhook_url IS NOT NULL AND discord_webhook_url != ''")
    ).fetchall()

    for row in rows:
        url = row[0]
        # Create a webhook entry with a generated name
        conn.execute(
            sa.text(
                "INSERT INTO discord_webhooks (name, url) VALUES (:name, :url)"
            ),
            {"name": f"Webhook ({url[-20:]})", "url": url},
        )

    # 4. Link rules to their new webhook entries
    conn.execute(
        sa.text(
            """
            UPDATE rules
            SET discord_webhook_id = dw.id
            FROM discord_webhooks dw
            WHERE rules.discord_webhook_url = dw.url
            """
        )
    )

    # 5. Drop the old column
    op.drop_column("rules", "discord_webhook_url")


def downgrade():
    # Re-add the old column
    op.add_column(
        "rules",
        sa.Column("discord_webhook_url", sa.String(500), nullable=True),
    )

    # Copy URLs back
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE rules
            SET discord_webhook_url = dw.url
            FROM discord_webhooks dw
            WHERE rules.discord_webhook_id = dw.id
            """
        )
    )

    op.drop_column("rules", "discord_webhook_id")
    op.drop_table("discord_webhooks")
