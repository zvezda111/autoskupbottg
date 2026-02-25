"""add spamblock_rub to UserPrice table

Revision ID: 3bf467b9062b
Revises: 4318c95bfd62
Create Date: 2025-08-02 18:24:33.896969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bf467b9062b'
down_revision: Union[str, Sequence[str], None] = '4318c95bfd62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_prices',
        sa.Column('spamblock_rub', sa.Integer(), nullable=False, server_default='0')
    )
    # если надо, можно убрать серверный дефолт после заполнения:
    op.alter_column('user_prices', 'spamblock_rub', server_default=None)


def downgrade() -> None:
    op.drop_column('user_prices', 'spamblock_rub')
