"""Add worker_trigger table

Revision ID: 0006_worker_trigger
Revises: 0005_add_ssl_mode
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_worker_trigger'
down_revision = '0005_add_ssl_mode'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'worker_triggers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('worker_triggers')
