"""Add scan_jobs and scan_results tables

Revision ID: a2b3c4d5e6f7
Revises: 5f6672803b73
Create Date: 2026-10-01 11:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '5f6672803b73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- scan_jobs ---
    op.create_table(
        'scan_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('center_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('centers.id'), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer()),
        sa.Column('total_pages', sa.Integer()),
        sa.Column('boards_found', sa.Integer(), server_default='0'),
        sa.Column('boards_approved', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('error_message', sa.Text()),
        sa.Column('processing_time_ms', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name='ck_status_enum'
        ),
    )
    op.create_index('ix_scan_jobs_center_id', 'scan_jobs', ['center_id'])
    op.create_index('ix_scan_jobs_uploaded_by', 'scan_jobs', ['uploaded_by'])
    op.create_index('ix_scan_jobs_status', 'scan_jobs', ['status'])

    # --- scan_results ---
    op.create_table(
        'scan_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('scan_jobs.id'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('board_index', sa.Integer(), nullable=False),
        sa.Column('board_image_url', sa.String(500)),
        sa.Column('bounding_box', postgresql.JSONB()),
        sa.Column('confidence_board', sa.Numeric(4, 2)),
        # FEN fields
        sa.Column('fen_candidate', sa.String(200)),
        sa.Column('fen_final', sa.String(200)),
        sa.Column('side_to_move', sa.String(1), server_default='w'),
        sa.Column('castling_rights', sa.String(4), server_default='-'),
        sa.Column('en_passant', sa.String(2), server_default='-'),
        # Per-cell confidence
        sa.Column('cell_confidence', postgresql.JSONB()),
        # Review
        sa.Column('review_status', sa.String(20), server_default='pending'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id')),
        sa.Column('reviewed_at', sa.DateTime(timezone=True)),
        # Link to puzzle
        sa.Column('puzzle_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('puzzles.id')),
        # Constraints
        sa.UniqueConstraint('job_id', 'page_number', 'board_index',
                            name='uq_scan_result_page_board'),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'corrected', 'rejected', 'auto_approved')",
            name='ck_review_status_enum'
        ),
    )
    op.create_index('ix_scan_results_job_id', 'scan_results', ['job_id'])
    op.create_index('ix_scan_results_review_status', 'scan_results', ['review_status'])


def downgrade() -> None:
    op.drop_table('scan_results')
    op.drop_table('scan_jobs')
