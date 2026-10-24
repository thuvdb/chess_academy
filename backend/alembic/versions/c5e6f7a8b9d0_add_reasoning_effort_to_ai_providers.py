"""add reasoning_effort to ai_providers

Revision ID: c5e6f7a8b9d0
Revises: b4f8a192c301
Create Date: 2026-10-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c5e6f7a8b9d0'
down_revision: Union[str, None] = 'b4f8a192c301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_providers', sa.Column('reasoning_effort', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_providers', 'reasoning_effort')
