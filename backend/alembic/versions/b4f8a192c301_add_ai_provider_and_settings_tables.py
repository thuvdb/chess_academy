"""add ai_provider and settings tables

Revision ID: b4f8a192c301
Revises: 3a71fd86fc48
Create Date: 2026-10-23 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b4f8a192c301'
down_revision: Union[str, None] = '3a71fd86fc48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ai_providers
    op.create_table(
        'ai_providers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('models', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 2. ai_settings
    op.create_table(
        'ai_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('default_provider_id', sa.UUID(), nullable=True),
        sa.Column('default_model', sa.String(length=100), nullable=False, server_default='gemini-3.8-flash'),
        sa.Column('fallback_provider_id', sa.UUID(), nullable=True),
        sa.Column('fallback_model', sa.String(length=100), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('max_output_tokens', sa.Integer(), nullable=False, server_default='1500'),
        sa.Column('request_timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['default_provider_id'], ['ai_providers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['fallback_provider_id'], ['ai_providers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. ai_settings_audit
    op.create_table(
        'ai_settings_audit',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('ai_settings_audit')
    op.drop_table('ai_settings')
    op.drop_table('ai_providers')
