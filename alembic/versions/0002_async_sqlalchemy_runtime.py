"""async sqlalchemy runtime

Revision ID: 0002_async_sqlalchemy_runtime
Revises: 0001_initial_schema
Create Date: 2026-05-08 00:00:01.000000
"""

from collections.abc import Sequence

revision: str = "0002_async_sqlalchemy_runtime"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
