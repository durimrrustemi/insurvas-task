"""discovery runs remember their partners

Revision ID: 5a7e9c1d2b4f
Revises: d740c678e382
"""

import sqlalchemy as sa
from alembic import op

revision = "5a7e9c1d2b4f"
down_revision = "d740c678e382"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("partner_ids", "new_partner_ids"):
        op.add_column(
            "discovery_runs",
            sa.Column(column, sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )


def downgrade() -> None:
    op.drop_column("discovery_runs", "new_partner_ids")
    op.drop_column("discovery_runs", "partner_ids")
