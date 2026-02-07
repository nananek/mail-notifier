"""Add account_id to Rule model

Revision ID: 0007_add_rule_account_id
Revises: 0006_worker_trigger
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007_add_rule_account_id'
down_revision = '0006_worker_trigger'
branch_labels = None
depends_on = None


def upgrade():
    # Add account_id column to rules table
    op.add_column('rules', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_rules_account_id', 'rules', 'accounts', ['account_id'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('fk_rules_account_id', 'rules', type_='foreignkey')
    op.drop_column('rules', 'account_id')
