"""Add deposit_percent to Calculation, amount to Document

Revision ID: bce91391b484
Revises: f86cd4b5ebb1
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bce91391b484'
down_revision: Union[str, None] = 'f86cd4b5ebb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('calculations', sa.Column('deposit_percent', sa.Numeric(precision=5, scale=2), nullable=True))
    op.execute("UPDATE calculations SET deposit_percent = 50 WHERE deposit_percent IS NULL")
    op.alter_column('calculations', 'deposit_percent', nullable=False)

    op.add_column('documents', sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'amount')
    op.drop_column('calculations', 'deposit_percent')
