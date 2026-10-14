"""add_center_admin_role

Revision ID: 4b2c1d9e8f7a
Revises: 3a1f8b7c4d2e
Create Date: 2026-10-14 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b2c1d9e8f7a'
down_revision: Union[str, None] = '3a1f8b7c4d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update check constraint on users role to include 'center_admin' alongside 'admin'
    op.drop_constraint('ck_role_enum', 'users', type_='check')
    op.create_check_constraint(
        'ck_role_enum',
        'users',
        "role IN ('super_admin', 'center_admin', 'admin', 'teacher', 'student', 'parent')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_role_enum', 'users', type_='check')
    op.create_check_constraint(
        'ck_role_enum',
        'users',
        "role IN ('super_admin', 'admin', 'teacher', 'student', 'parent')",
    )
