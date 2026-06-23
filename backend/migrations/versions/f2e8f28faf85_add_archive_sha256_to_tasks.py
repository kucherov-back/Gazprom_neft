"""add archive_sha256 to tasks

Revision ID: f2e8f28faf85
Revises:
Create Date: 2026-06-23 21:02:58.745783

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2e8f28faf85"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "DONE", "ERROR", name="taskstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("archive_sha256", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_tasks_archive_sha256"), ["archive_sha256"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tasks_archive_sha256"))

    op.drop_table("tasks")
