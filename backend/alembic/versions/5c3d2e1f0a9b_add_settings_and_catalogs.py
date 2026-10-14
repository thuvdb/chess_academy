"""add_settings_and_catalogs

Revision ID: 5c3d2e1f0a9b
Revises: 4b2c1d9e8f7a
Create Date: 2026-10-14 17:15:00.000000

"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '5c3d2e1f0a9b'
down_revision: Union[str, None] = '4b2c1d9e8f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create catalog_items table
    op.create_table(
        'catalog_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('center_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('centers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('catalog_type', sa.String(50), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.UniqueConstraint('catalog_type', 'code', 'center_id', name='uq_catalog_type_code_center'),
    )
    op.create_index('ix_catalog_items_center_id', 'catalog_items', ['center_id'])
    op.create_index('ix_catalog_items_catalog_type', 'catalog_items', ['catalog_type'])

    # 2. Create settings table
    op.create_table(
        'settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('center_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('centers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(20), nullable=False, server_default='string'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='general'),
        sa.Column('is_overridable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True),
        sa.UniqueConstraint('key', 'center_id', name='uq_setting_key_center'),
    )
    op.create_index('ix_settings_center_id', 'settings', ['center_id'])
    op.create_index('ix_settings_key', 'settings', ['key'])

    # 3. Seed default system catalogs and settings
    catalog_table = sa.table(
        'catalog_items',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('center_id', postgresql.UUID(as_uuid=True)),
        sa.column('catalog_type', sa.String),
        sa.column('code', sa.String),
        sa.column('label', sa.String),
        sa.column('order_index', sa.Integer),
        sa.column('is_active', sa.Boolean),
    )

    settings_table = sa.table(
        'settings',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('center_id', postgresql.UUID(as_uuid=True)),
        sa.column('key', sa.String),
        sa.column('value', sa.Text),
        sa.column('value_type', sa.String),
        sa.column('description', sa.Text),
        sa.column('category', sa.String),
        sa.column('is_overridable', sa.Boolean),
    )

    default_catalogs = [
        # course_level
        ('course_level', 'beginner', 'Cơ bản', 1),
        ('course_level', 'intermediate', 'Trung cấp', 2),
        ('course_level', 'advanced', 'Nâng cao', 3),
        ('course_level', 'master', 'Chuyên sâu', 4),
        # puzzle_theme
        ('puzzle_theme', 'fork', 'Bắt đôi (Fork)', 1),
        ('puzzle_theme', 'pin', 'Ghim quân (Pin)', 2),
        ('puzzle_theme', 'skewer', 'Xiên (Skewer)', 3),
        ('puzzle_theme', 'discovered_attack', 'Tấn công mở', 4),
        ('puzzle_theme', 'double_check', 'Chiếu kép', 5),
        ('puzzle_theme', 'back_rank', 'Hàng ngang cuối', 6),
        ('puzzle_theme', 'deflection', 'Đánh lạc hướng', 7),
        # puzzle_difficulty_band
        ('puzzle_difficulty_band', 'easy', 'Dễ (< 1000)', 1),
        ('puzzle_difficulty_band', 'medium', 'Trung bình (1000 - 1500)', 2),
        ('puzzle_difficulty_band', 'hard', 'Khó (> 1500)', 3),
        # parent_relationship
        ('parent_relationship', 'father', 'Bố', 1),
        ('parent_relationship', 'mother', 'Mẹ', 2),
        ('parent_relationship', 'guardian', 'Người giám hộ', 3),
        ('parent_relationship', 'other', 'Khác', 4),
        # class_status
        ('class_status', 'active', 'Đang mở', 1),
        ('class_status', 'upcoming', 'Sắp khai giảng', 2),
        ('class_status', 'completed', 'Đã hoàn thành', 3),
        # enrollment_status
        ('enrollment_status', 'active', 'Đang học', 1),
        ('enrollment_status', 'reserved', 'Bảo lưu', 2),
        ('enrollment_status', 'dropped', 'Nghỉ học', 3),
        # currency
        ('currency', 'VND', 'Việt Nam Đồng (đ)', 1),
        # class_schedule_slot
        ('class_schedule_slot', 'slot_1', '08:00 - 09:30', 1),
        ('class_schedule_slot', 'slot_2', '09:45 - 11:15', 2),
        ('class_schedule_slot', 'slot_3', '14:00 - 15:30', 3),
        ('class_schedule_slot', 'slot_4', '15:45 - 17:15', 4),
        ('class_schedule_slot', 'slot_5', '18:00 - 19:30', 5),
        ('class_schedule_slot', 'slot_6', '19:45 - 21:15', 6),
    ]

    catalog_rows = [
        {
            'id': uuid.uuid4(),
            'center_id': None,
            'catalog_type': cat_type,
            'code': code,
            'label': label,
            'order_index': idx,
            'is_active': True,
        }
        for cat_type, code, label, idx in default_catalogs
    ]
    op.bulk_insert(catalog_table, catalog_rows)

    default_settings = [
        ('system_name', 'CAMS - Chess Academy Management System', 'string', 'Tên hệ thống', 'general', False),
        ('allow_public_register', 'false', 'bool', 'Cho phép tự do đăng ký tài khoản học sinh', 'security', False),
        ('rating_initial', '800', 'int', 'Điểm Elo/Rating khởi tạo cho học viên mới', 'rating', False),
        ('k_factor_low', '32', 'int', 'Hệ số K khi rating < 1200', 'rating', True),
        ('k_factor_high', '16', 'int', 'Hệ số K khi rating >= 2000', 'rating', True),
        ('hint_penalty', '5', 'int', 'Số điểm trừ khi học sinh dùng gợi ý', 'rating', True),
        ('stockfish_depth', '10', 'int', 'Độ sâu tìm kiếm mặc định của Stockfish engine', 'engine', True),
        ('stockfish_time_limit', '1.0', 'float', 'Thời gian tính toán tối đa của Stockfish (giây)', 'engine', True),
        ('max_upload_size_mb', '50', 'int', 'Dung lượng file PDF tải lên tối đa (MB)', 'scanner', True),
        ('max_upload_pages', '20', 'int', 'Số trang quét tối đa mỗi lượt PDF', 'scanner', True),
    ]

    setting_rows = [
        {
            'id': uuid.uuid4(),
            'center_id': None,
            'key': key,
            'value': val,
            'value_type': vtype,
            'description': desc,
            'category': cat,
            'is_overridable': ovr,
        }
        for key, val, vtype, desc, cat, ovr in default_settings
    ]
    op.bulk_insert(settings_table, setting_rows)


def downgrade() -> None:
    op.drop_table('settings')
    op.drop_table('catalog_items')
