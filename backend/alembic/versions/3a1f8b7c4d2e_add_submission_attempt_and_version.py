"""add_submission_attempt_and_version

Revision ID: 3a1f8b7c4d2e
Revises: 28f9f6aa55d2
Create Date: 2026-10-13 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a1f8b7c4d2e'
down_revision: Union[str, None] = '28f9f6aa55d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update check constraint on assignment_submissions status to include 'reopened'
    op.drop_constraint('ck_assignment_submission_status_enum', 'assignment_submissions', type_='check')
    op.create_check_constraint(
        'ck_assignment_submission_status_enum',
        'assignment_submissions',
        "status IN ('not_started', 'in_progress', 'submitted', 'graded', 'returned', 'reopened')",
    )

    # 2. Add attempt_no and version columns to assignment_submissions
    op.add_column(
        'assignment_submissions',
        sa.Column('attempt_no', sa.Integer(), server_default='1', nullable=False),
    )
    op.add_column(
        'assignment_submissions',
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    )

    # 3. Replace unique constraint on (assignment_id, student_id) with (assignment_id, student_id, attempt_no)
    # Check if index exists or drop index
    op.execute("DROP INDEX IF EXISTS uq_assignment_submission_student;")
    op.execute("ALTER TABLE assignment_submissions DROP CONSTRAINT IF EXISTS uq_assignment_submission_student;")
    op.create_index(
        'uq_assignment_submission_attempt',
        'assignment_submissions',
        ['assignment_id', 'student_id', 'attempt_no'],
        unique=True,
    )

    # 4. Add submission_id to student_attempts
    op.add_column(
        'student_attempts',
        sa.Column(
            'submission_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('assignment_submissions.id', ondelete='CASCADE'),
            nullable=True,
        ),
    )
    op.create_index(
        'ix_student_attempts_submission_id',
        'student_attempts',
        ['submission_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_student_attempts_submission_id', table_name='student_attempts')
    op.drop_column('student_attempts', 'submission_id')

    op.drop_index('uq_assignment_submission_attempt', table_name='assignment_submissions')
    op.create_index(
        'uq_assignment_submission_student',
        'assignment_submissions',
        ['assignment_id', 'student_id'],
        unique=True,
    )

    op.drop_column('assignment_submissions', 'version')
    op.drop_column('assignment_submissions', 'attempt_no')

    op.drop_constraint('ck_assignment_submission_status_enum', 'assignment_submissions', type_='check')
    op.create_check_constraint(
        'ck_assignment_submission_status_enum',
        'assignment_submissions',
        "status IN ('not_started', 'in_progress', 'submitted', 'graded', 'returned')",
    )
