"""add_grading_fields_to_submissions

Revision ID: 28f9f6aa55d2
Revises: f920da3e1b23
Create Date: 2026-10-13 09:24:02.166003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28f9f6aa55d2'
down_revision: Union[str, None] = 'f920da3e1b23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.add_column(
        'assignment_submissions',
        sa.Column('teacher_feedback', sa.Text(), nullable=True),
    )
    op.add_column(
        'assignment_submissions',
        sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'assignment_submissions',
        sa.Column('graded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )
    op.add_column(
        'assignment_submissions',
        sa.Column('teacher_adjustment', sa.Integer(), server_default='0', nullable=False),
    )

    op.drop_constraint('ck_assignment_submission_status_enum', 'assignment_submissions', type_='check')
    op.create_check_constraint(
        'ck_assignment_submission_status_enum',
        'assignment_submissions',
        "status IN ('not_started', 'in_progress', 'submitted', 'graded', 'returned')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_assignment_submission_status_enum', 'assignment_submissions', type_='check')
    op.create_check_constraint(
        'ck_assignment_submission_status_enum',
        'assignment_submissions',
        "status IN ('not_started', 'in_progress', 'submitted', 'graded')",
    )
    op.drop_column('assignment_submissions', 'teacher_adjustment')
    op.drop_column('assignment_submissions', 'graded_by')
    op.drop_column('assignment_submissions', 'graded_at')
    op.drop_column('assignment_submissions', 'teacher_feedback')

