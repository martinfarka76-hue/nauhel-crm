"""Add customer_type to Company (backfilled by IČO presence)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

customertype = sa.Enum('Spotřebitel', 'Podnikatel', name='customertype')


def upgrade() -> None:
    customertype.create(op.get_bind(), checkfirst=True)
    op.add_column('companies', sa.Column('customer_type', customertype, nullable=True))
    op.execute(
        "UPDATE companies SET customer_type = 'Podnikatel' "
        "WHERE ico IS NOT NULL AND btrim(ico) <> ''"
    )
    op.execute(
        "UPDATE companies SET customer_type = 'Spotřebitel' "
        "WHERE customer_type IS NULL"
    )
    op.alter_column('companies', 'customer_type', nullable=False)


def downgrade() -> None:
    op.drop_column('companies', 'customer_type')
    customertype.drop(op.get_bind(), checkfirst=True)
