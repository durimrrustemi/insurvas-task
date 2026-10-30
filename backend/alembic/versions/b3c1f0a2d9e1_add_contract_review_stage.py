"""add contract_review stage

Revision ID: b3c1f0a2d9e1
Revises: 5a7e9c1d2b4f
"""

from alembic import op

revision = "b3c1f0a2d9e1"
down_revision = "5a7e9c1d2b4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE stage ADD VALUE IF NOT EXISTS 'CONTRACT_REVIEW' AFTER 'TEST_CALLS'")


def downgrade() -> None:
    # Postgres cannot drop a value from an enum type; leaving it is harmless.
    pass
