"""Add unique index on student_progress to prevent duplicate attempts and progress records

Revision ID: e819fa2c4d11
Revises: c3a7f1b9d204
Create Date: 2026-10-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e819fa2c4d11'
down_revision: Union[str, None] = 'c3a7f1b9d204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_student_puzzle_assignment "
        "ON student_progress (student_id, puzzle_id, assignment_id) NULLS NOT DISTINCT"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_student_puzzle_assignment")
