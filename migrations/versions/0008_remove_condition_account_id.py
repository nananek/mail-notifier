"""Remove account_id from RuleCondition

Revision ID: 0008_remove_condition_account_id
Revises: 0007_add_rule_account_id
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008_remove_condition_account_id'
down_revision = '0007_add_rule_account_id'
branch_labels = None
depends_on = None


def upgrade():
    # Drop foreign key and column from rule_conditions
    op.drop_constraint('rule_conditions_account_id_fkey', 'rule_conditions', type_='foreignkey')
    op.drop_column('rule_conditions', 'account_id')


def downgrade():
    # Add back the column and foreign key
    op.add_column('rule_conditions', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_foreign_key('rule_conditions_account_id_fkey', 'rule_conditions', 'accounts', ['account_id'], ['id'], ondelete='SET NULL')
