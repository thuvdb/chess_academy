"""Add assignment_submissions table for hard submission lock and audit log

Revision ID: f920da3e1b23
Revises: e819fa2c4d11
Create Date: 2026-10-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f920da3e1b23'
down_revision: Union[str, None] = 'e819fa2c4d11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'assignment_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assignments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='in_progress', nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_points', sa.Integer(), server_default='0', nullable=False),
        sa.Column('completed_puzzles', sa.Integer(), server_default='0', nullable=False),
        sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reopened_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reopen_reason', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'submitted', 'graded')",
            name='ck_assignment_submission_status_enum',
        ),
    )
    op.create_index(
        'uq_assignment_submission_student',
        'assignment_submissions',
        ['assignment_id', 'student_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_assignment_submission_student', table_name='assignment_submissions')
    op.drop_table('assignment_submissions')
