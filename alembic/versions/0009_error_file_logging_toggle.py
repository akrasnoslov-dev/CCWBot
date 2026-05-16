"""error file logging toggle

Revision ID: 0009_error_file_logging_toggle
Revises: 0008_database_comments
Create Date: 2026-05-16

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0009_error_file_logging_toggle"
down_revision: str | None = "0008_database_comments"
branch_labels: str | None = None
depends_on: str | None = None


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "error_file_logging_enabled" not in _column_names("app_settings"):
        op.add_column(
            "app_settings",
            sa.Column(
                "error_file_logging_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
                comment="Whether admins enabled persistent WARNING and ERROR file logging.",
            ),
        )


def downgrade() -> None:
    if "error_file_logging_enabled" in _column_names("app_settings"):
        op.drop_column("app_settings", "error_file_logging_enabled")
