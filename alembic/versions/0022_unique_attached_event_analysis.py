"""unique attached event analysis

Revision ID: 0022_unique_attached_event_analysis
Revises: 0021_alert_delivery_outcomes
Create Date: 2026-06-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_unique_attached_event_analysis"
down_revision: str | None = "0021_alert_delivery_outcomes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_event_ai_analyses_one_attached_event_analysis_per_event"
INDEX_PREDICATE = (
    "market_event_id IS NOT NULL "
    "AND analysis_type = 'event_analysis'"
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE event_ai_analyses
            SET market_event_id = NULL
            WHERE market_event_id IS NOT NULL
              AND analysis_type = 'event_analysis'
              AND (
                status NOT IN ('success', 'completed')
                OR should_alert IS NOT TRUE
              )
            """
        )
    )
    # Preserve duplicate evidence by detaching non-canonical rows before the
    # unique index is created. Canonical = delivery-referenced first, then oldest.
    op.execute(
        sa.text(
            """
            UPDATE event_ai_analyses
            SET market_event_id = NULL
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        eaa.id,
                        ROW_NUMBER() OVER (
                            PARTITION BY eaa.market_event_id
                            ORDER BY
                                CASE
                                    WHEN EXISTS (
                                        SELECT 1
                                        FROM alerts a
                                        WHERE a.event_ai_analysis_id = eaa.id
                                    )
                                    OR EXISTS (
                                        SELECT 1
                                        FROM alert_delivery_outcomes ado
                                        WHERE ado.event_ai_analysis_id = eaa.id
                                    )
                                    THEN 0
                                    ELSE 1
                                END,
                                eaa.id ASC
                        ) AS row_number
                    FROM event_ai_analyses eaa
                    WHERE eaa.market_event_id IS NOT NULL
                      AND eaa.analysis_type = 'event_analysis'
                      AND eaa.status IN ('success', 'completed')
                      AND eaa.should_alert IS TRUE
                ) ranked
                WHERE row_number > 1
            )
            """
        )
    )
    op.create_index(
        INDEX_NAME,
        "event_ai_analyses",
        ["market_event_id"],
        unique=True,
        sqlite_where=sa.text(INDEX_PREDICATE),
        postgresql_where=sa.text(INDEX_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="event_ai_analyses")
