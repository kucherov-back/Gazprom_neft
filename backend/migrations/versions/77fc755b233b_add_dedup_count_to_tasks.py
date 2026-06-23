"""add dedup_count to tasks

Revision ID: 77fc755b233b
Revises: f2e8f28faf85
Create Date: 2026-06-23 21:44:39.554811

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "77fc755b233b"
down_revision: str | Sequence[str] | None = "f2e8f28faf85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("dedup_count", sa.Integer(), server_default="0", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_column("dedup_count")
