"""structured news intelligence cache

Revision ID: 0020_news_items
Revises: 0019_heartbeat_idemp
Create Date: 2026-05-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_news_items"
down_revision: str | None = "0019_heartbeat_idemp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), nullable=False, comment="Internal structured news row id."),
        sa.Column(
            "news_key",
            sa.String(length=500),
            nullable=False,
            comment="Stable news identity compatible with seen_news keys.",
        ),
        sa.Column(
            "title",
            sa.String(length=1000),
            nullable=False,
            comment="Normalized RSS title for this news item.",
        ),
        sa.Column(
            "source",
            sa.String(length=255),
            nullable=True,
            comment="Normalized publisher or feed source.",
        ),
        sa.Column(
            "url",
            sa.String(length=2000),
            nullable=False,
            comment="Normalized article URL from RSS metadata.",
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Publication timestamp from RSS metadata.",
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this item was last fetched.",
        ),
        sa.Column(
            "raw_summary",
            sa.Text(),
            nullable=True,
            comment="Compact RSS summary or description before LLM analysis.",
        ),
        sa.Column(
            "llm_summary",
            sa.Text(),
            nullable=True,
            comment="Validated short user-facing summary returned by the LLM.",
        ),
        sa.Column(
            "llm_raw_response",
            sa.Text(),
            nullable=True,
            comment="Raw compact JSON response returned by the news LLM.",
        ),
        sa.Column(
            "related_symbols",
            sa.JSON(),
            nullable=True,
            comment="Lowercase supported symbols related to this news item.",
        ),
        sa.Column(
            "primary_symbol",
            sa.String(length=32),
            nullable=True,
            comment="Primary lowercase supported symbol selected for the item.",
        ),
        sa.Column(
            "category",
            sa.String(length=64),
            nullable=True,
            comment="Validated news category such as market or regulation.",
        ),
        sa.Column(
            "impact_score",
            sa.Integer(),
            nullable=True,
            comment="Validated impact score from 0 to 100.",
        ),
        sa.Column(
            "impact_level",
            sa.String(length=32),
            nullable=True,
            comment="Validated impact level such as low or high.",
        ),
        sa.Column(
            "relevance_score",
            sa.Integer(),
            nullable=True,
            comment="Validated relevance score from 0 to 100.",
        ),
        sa.Column(
            "dedup_group_id",
            sa.String(length=128),
            nullable=True,
            comment="Stable group id for duplicate or similar news items.",
        ),
        sa.Column(
            "is_duplicate",
            sa.Boolean(),
            nullable=False,
            comment="Whether this item duplicates a previously processed item.",
        ),
        sa.Column(
            "is_noise",
            sa.Boolean(),
            nullable=False,
            comment="Whether this item is low-quality or not useful context.",
        ),
        sa.Column(
            "is_alert_worthy",
            sa.Boolean(),
            nullable=False,
            comment="Whether intelligence considers the item alert-worthy later.",
        ),
        sa.Column(
            "llm_provider",
            sa.String(length=64),
            nullable=True,
            comment="LLM provider used for news intelligence.",
        ),
        sa.Column(
            "llm_model",
            sa.String(length=255),
            nullable=True,
            comment="LLM model used for news intelligence.",
        ),
        sa.Column(
            "llm_input_hash",
            sa.String(length=64),
            nullable=True,
            comment="SHA-256 hash of the compact LLM input payload.",
        ),
        sa.Column(
            "llm_status",
            sa.String(length=64),
            nullable=False,
            comment="News intelligence status such as success or skipped.",
        ),
        sa.Column(
            "llm_error",
            sa.Text(),
            nullable=True,
            comment="Sanitized news intelligence error message, if any.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this structured news row was created.",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this structured news row was last updated.",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("news_key", name="uq_news_items_news_key"),
        comment="Structured RSS news intelligence cached before alert selection.",
    )
    op.create_index("ix_news_items_news_key", "news_items", ["news_key"])
    op.create_index("ix_news_items_published_at", "news_items", ["published_at"])
    op.create_index("ix_news_items_primary_symbol", "news_items", ["primary_symbol"])
    op.create_index("ix_news_items_category", "news_items", ["category"])
    op.create_index("ix_news_items_impact_level", "news_items", ["impact_level"])
    op.create_index("ix_news_items_dedup_group_id", "news_items", ["dedup_group_id"])
    op.create_index("ix_news_items_llm_status", "news_items", ["llm_status"])


def downgrade() -> None:
    op.drop_index("ix_news_items_llm_status", table_name="news_items")
    op.drop_index("ix_news_items_dedup_group_id", table_name="news_items")
    op.drop_index("ix_news_items_impact_level", table_name="news_items")
    op.drop_index("ix_news_items_category", table_name="news_items")
    op.drop_index("ix_news_items_primary_symbol", table_name="news_items")
    op.drop_index("ix_news_items_published_at", table_name="news_items")
    op.drop_index("ix_news_items_news_key", table_name="news_items")
    op.drop_table("news_items")
