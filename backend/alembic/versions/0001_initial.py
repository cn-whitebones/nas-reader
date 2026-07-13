"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    user_role = postgresql.ENUM("admin", "user", name="userrole")
    source_type = postgresql.ENUM("book", "comic", "mixed", name="sourcetype")
    scan_status = postgresql.ENUM("pending", "running", "done", "failed", name="scanstatus")
    book_format = postgresql.ENUM("txt", "epub", "pdf", "mobi", "comic", name="bookformat")
    book_status = postgresql.ENUM("active", "missing", name="bookstatus")
    provider = postgresql.ENUM("douban", "google", "openlibrary", "manual", name="metadataprovidername")

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # sources
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("root_path", sa.String(1024), nullable=False),
        sa.Column("type", source_type, nullable=False),
        sa.Column("auto_scan", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("scan_interval_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("root_path", name="uq_source_root_path"),
    )

    # permissions
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sub_path", sa.String(1024), nullable=True),
        sa.Column("can_read", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("user_id", "source_id", "sub_path", name="uq_permission_scope"),
    )
    op.create_index("ix_permissions_user_id", "permissions", ["user_id"])
    op.create_index("ix_permissions_source_id", "permissions", ["source_id"])

    # scan_tasks
    op.create_table(
        "scan_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE")),
        sa.Column("status", scan_status, nullable=False),
        sa.Column("total", sa.Integer, server_default="0"),
        sa.Column("processed", sa.Integer, server_default="0"),
        sa.Column("added", sa.Integer, server_default="0"),
        sa.Column("updated", sa.Integer, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scan_tasks_source_id", "scan_tasks", ["source_id"])

    # books
    op.create_table(
        "books",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE")),
        sa.Column("rel_path", sa.String(2048), nullable=False),
        sa.Column("dir_path", sa.String(2048), server_default=""),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("format", book_format, nullable=False),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("file_size", sa.BigInteger, server_default="0"),
        sa.Column("cover_path", sa.String(1024), nullable=True),
        sa.Column("status", book_status, nullable=False),
        sa.Column("chapter_count", sa.Integer, server_default="0"),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_id", "rel_path", name="uq_book_source_path"),
    )
    op.create_index("ix_books_source_id", "books", ["source_id"])
    op.create_index("ix_books_rel_path", "books", ["rel_path"])
    op.create_index("ix_books_dir_path", "books", ["dir_path"])
    op.create_index("ix_books_file_hash", "books", ["file_hash"])
    op.create_index("ix_books_format", "books", ["format"])
    op.create_index("ix_books_status", "books", ["status"])
    # 文件名全文/相似搜索(pg_trgm)
    op.create_index(
        "ix_books_file_name_trgm", "books", ["file_name"],
        postgresql_using="gin", postgresql_ops={"file_name": "gin_trgm_ops"},
    )

    # book_metadata
    op.create_table(
        "book_metadata",
        sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("subtitle", sa.String(512), nullable=True),
        sa.Column("authors", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("publisher", sa.String(256), nullable=True),
        sa.Column("isbn", sa.String(32), nullable=True),
        sa.Column("pub_date", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("rating", sa.Float, nullable=True),
        sa.Column("douban_id", sa.String(32), nullable=True),
        sa.Column("source_provider", provider, nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_book_metadata_title", "book_metadata", ["title"])
    op.create_index("ix_book_metadata_isbn", "book_metadata", ["isbn"])
    op.create_index(
        "ix_book_metadata_title_trgm", "book_metadata", ["title"],
        postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index("ix_book_metadata_tags", "book_metadata", ["tags"], postgresql_using="gin")

    # chapters
    op.create_table(
        "chapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE")),
        sa.Column("idx", sa.Integer, nullable=False),
        sa.Column("title", sa.String(512), server_default=""),
        sa.Column("location", sa.String(1024), server_default=""),
        sa.UniqueConstraint("book_id", "idx", name="uq_chapter_book_idx"),
    )
    op.create_index("ix_chapters_book_id", "chapters", ["book_id"])

    # shelves
    op.create_table(
        "shelves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "name", name="uq_shelf_user_name"),
    )
    op.create_index("ix_shelves_user_id", "shelves", ["user_id"])

    # shelf_books
    op.create_table(
        "shelf_books",
        sa.Column("shelf_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shelves.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # reading_progress
    op.create_table(
        "reading_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE")),
        sa.Column("location", sa.String(1024), server_default=""),
        sa.Column("percent", sa.Float, server_default="0"),
        sa.Column("chapter_idx", sa.Integer, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "book_id", name="uq_progress_user_book"),
    )
    op.create_index("ix_reading_progress_user_id", "reading_progress", ["user_id"])
    op.create_index("ix_reading_progress_book_id", "reading_progress", ["book_id"])

    # reading_settings
    op.create_table(
        "reading_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("font_family", sa.String(128), server_default="serif"),
        sa.Column("font_size", sa.Integer, server_default="18"),
        sa.Column("line_height", sa.Float, server_default="1.6"),
        sa.Column("margin", sa.Integer, server_default="16"),
        sa.Column("theme", sa.String(16), server_default="light"),
        sa.Column("extra", postgresql.JSONB, server_default="{}"),
    )


def downgrade() -> None:
    for table in [
        "reading_settings", "reading_progress", "shelf_books", "shelves",
        "chapters", "book_metadata", "books", "scan_tasks", "permissions",
        "sources", "users",
    ]:
        op.drop_table(table)
    for enum_name in [
        "metadataprovidername", "bookstatus", "bookformat", "scanstatus",
        "sourcetype", "userrole",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
