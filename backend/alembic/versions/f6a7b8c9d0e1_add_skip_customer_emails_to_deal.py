"""Add skip_customer_emails to Deal (manual government-form exception)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deals',
        sa.Column('skip_customer_emails', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('deals', 'skip_customer_emails', server_default=None)


def downgrade() -> None:
    op.drop_column('deals', 'skip_customer_emails')
