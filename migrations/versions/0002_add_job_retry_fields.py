"""add job retry fields

Revision ID: 0002_add_job_retry_fields
Revises: 0001_create_jobs
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_job_retry_fields"
down_revision: str | None = "0001_create_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
    )
    op.add_column("jobs", sa.Column("error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "error")
    op.drop_column("jobs", "max_attempts")
    op.drop_column("jobs", "attempts")
