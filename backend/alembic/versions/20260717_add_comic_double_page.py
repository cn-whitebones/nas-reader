"""add comic double page fields

Revision ID: 20260717_add_comic_double_page
Revises: d4c35787e379
Create Date: 2026-07-17 20:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260717_add_comic_double_page'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        # 添加双页相关字段
        batch_op.add_column(sa.Column('double_page', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('start_right', sa.Boolean(), nullable=True))
    # 设置默认值
    op.execute("UPDATE books SET double_page = 0 WHERE double_page IS NULL")
    op.execute("UPDATE books SET start_right = 0 WHERE start_right IS NULL")


def downgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.drop_column('double_page')
        batch_op.drop_column('start_right')
