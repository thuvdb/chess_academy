"""Add solution tree and verification flags to puzzles

Lời giải cũ lưu dưới dạng một mảng phẳng trộn lẫn nước của hai bên và không hề
được kiểm chứng. Migration này thêm cây biến thể (JSONB) cùng các cờ xác thực,
và thêm cột `side` cho main line để không còn lẫn bên.

Revision ID: c3a7f1b9d204
Revises: d726207be4a1
Create Date: 2026-10-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3a7f1b9d204'
down_revision: Union[str, None] = 'd726207be4a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Giữ khớp với app.models.base.PuzzleType
PUZZLE_TYPES_NEW = (
    'tactic', 'endgame', 'opening', 'strategy', 'custom',
    'mate_in_1', 'mate_in_2', 'mate_in_3', 'mate_in_4',
)
PUZZLE_TYPES_OLD = (
    'tactic', 'endgame', 'opening', 'strategy', 'custom',
    'mate_in_1', 'mate_in_2', 'mate_in_3',
)


def _type_check(values: Sequence[str]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"puzzle_type IN ({joined})"


def upgrade() -> None:
    op.add_column('puzzles', sa.Column('solution_tree', postgresql.JSONB(), nullable=True))
    op.add_column('puzzles', sa.Column('mate_in', sa.Integer(), nullable=True))
    op.add_column(
        'puzzles',
        sa.Column('solution_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'puzzles',
        sa.Column('solution_verified_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column('puzzles', sa.Column('verification_error', sa.Text(), nullable=True))

    op.add_column('puzzle_solutions', sa.Column('side', sa.String(length=1), nullable=True))

    # Mở rộng enum puzzle_type để chứa mate_in_4 (solver phát hiện tới 4 nước)
    op.drop_constraint('ck_puzzle_type_enum', 'puzzles', type_='check')
    op.create_check_constraint('ck_puzzle_type_enum', 'puzzles', _type_check(PUZZLE_TYPES_NEW))


def downgrade() -> None:
    # Gộp mate_in_4 về tactic trước khi thu hẹp constraint, nếu không sẽ fail
    op.execute("UPDATE puzzles SET puzzle_type = 'tactic' WHERE puzzle_type = 'mate_in_4'")
    op.drop_constraint('ck_puzzle_type_enum', 'puzzles', type_='check')
    op.create_check_constraint('ck_puzzle_type_enum', 'puzzles', _type_check(PUZZLE_TYPES_OLD))

    op.drop_column('puzzle_solutions', 'side')
    op.drop_column('puzzles', 'verification_error')
    op.drop_column('puzzles', 'solution_verified_at')
    op.drop_column('puzzles', 'solution_verified')
    op.drop_column('puzzles', 'mate_in')
    op.drop_column('puzzles', 'solution_tree')
