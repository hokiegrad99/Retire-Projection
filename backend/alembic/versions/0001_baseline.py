"""Baseline schema revision.

Phase 0 (INFRA-001) establishes the migration pipeline only.  The first
financial domain tables arrive with DATA-001 in Phase 1, so this revision
intentionally creates no tables.
"""

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No tables yet; Phase 1 introduces the financial domain schema."""


def downgrade() -> None:
    """No-op: the baseline has no preceding revision."""
