"""Fix customertype enum labels to match SQLAlchemy name convention

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE customertype RENAME VALUE 'Spotřebitel' TO 'SPOTREBITEL'")
    op.execute("ALTER TYPE customertype RENAME VALUE 'Podnikatel' TO 'PODNIKATEL'")


def downgrade() -> None:
    op.execute("ALTER TYPE customertype RENAME VALUE 'SPOTREBITEL' TO 'Spotřebitel'")
    op.execute("ALTER TYPE customertype RENAME VALUE 'PODNIKATEL' TO 'Podnikatel'")
