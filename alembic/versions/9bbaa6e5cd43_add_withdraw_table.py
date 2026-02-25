"""Add withdraw table

Revision ID: 9bbaa6e5cd43
Revises: 9612468fb354
Create Date: 2025-08-01 14:30:52.232880

"""
from typing import Sequence, Union

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = '9bbaa6e5cd43'
down_revision: Union[str, Sequence[str], None] = '9612468fb354'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ Явно создаём ENUM-тип (если его ещё нет)
    withdrawstatus = ENUM(
        'pending', 'approved', 'rejected',
        name='withdrawstatus'
    )
    withdrawstatus.create(op.get_bind(), checkfirst=True)

    # 2️⃣ Создаём таблицу, но говорим не создавать тип заново
    status_col = ENUM(
        'pending', 'approved', 'rejected',
        name='withdrawstatus',
        create_type=False
    )

    op.create_table(
        'withdrawals',
        sa.Column('id', sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('status', status_col, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_withdrawals_id', 'withdrawals', ['id'], unique=False)

    # Если вам не нужен конверт users.id, этот блок можно убрать
    op.alter_column('users', 'id',
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        autoincrement=True,
        existing_server_default=sa.text("nextval('users_id_seq'::regclass)")
    )


def downgrade() -> None:
    op.drop_index('ix_withdrawals_id', table_name='withdrawals')
    op.drop_table('withdrawals')

    # Удаляем ENUM-тип
    withdrawstatus = ENUM(name='withdrawstatus')
    withdrawstatus.drop(op.get_bind(), checkfirst=True)

    # Откат users.id, если он был BigInteger
    op.alter_column('users', 'id',
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
        autoincrement=True,
        existing_server_default=sa.text("nextval('users_id_seq'::regclass)")
    )