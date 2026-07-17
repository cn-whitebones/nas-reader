"""add word_count and pinyin sort keys

Revision ID: a1b2c3d4e5f6
Revises: d4c35787e379
Create Date: 2026-07-17 04:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d4c35787e379"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # books.word_count:txt/epub/mobi 精确统计,pdf/漫画为 NULL
    with op.batch_alter_table("books") as batch:
        batch.add_column(sa.Column("word_count", sa.Integer(), nullable=True))
        batch.create_index("ix_books_word_count", ["word_count"])

    # book_metadata.title_sort / author_sort:拼音排序键
    with op.batch_alter_table("book_metadata") as batch:
        batch.add_column(sa.Column("title_sort", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("author_sort", sa.String(length=512), nullable=True))
        batch.create_index("ix_book_metadata_title_sort", ["title_sort"])
        batch.create_index("ix_book_metadata_author_sort", ["author_sort"])


def downgrade() -> None:
    with op.batch_alter_table("book_metadata") as batch:
        batch.drop_index("ix_book_metadata_author_sort")
        batch.drop_index("ix_book_metadata_title_sort")
        batch.drop_column("author_sort")
        batch.drop_column("title_sort")
    with op.batch_alter_table("books") as batch:
        batch.drop_index("ix_books_word_count")
        batch.drop_column("word_count")
