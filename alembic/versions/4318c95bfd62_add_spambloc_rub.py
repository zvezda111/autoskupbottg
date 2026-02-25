"""add spambloc_rub

Revision ID: 4318c95bfd62
Revises: 88a779c5e7c5
Create Date: 2025-08-01 18:59:24.834734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4318c95bfd62'
down_revision: Union[str, Sequence[str], None] = '88a779c5e7c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('prices', sa.Column('spamblock_rub', sa.Integer(), nullable=False, server_default="0"))

def downgrade():
    op.drop_column('prices', 'spamblock_rub')