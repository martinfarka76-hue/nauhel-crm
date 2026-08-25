"""Add agreed_to_terms to Document

Revision ID: 441344860bdf
Revises: c04109817d70
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441344860bdf'
down_revision: Union[str, None] = 'c04109817d70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('agreed_to_terms', sa.Boolean(), nullable=True))
    op.execute("UPDATE documents SET agreed_to_terms = false WHERE agreed_to_terms IS NULL")
    op.alter_column('documents', 'agreed_to_terms', nullable=False)


def downgrade() -> None:
    op.drop_column('documents', 'agreed_to_terms')
