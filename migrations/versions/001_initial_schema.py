"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('language_code', sa.String(10), nullable=False, default='en'),
        sa.Column('timezone', sa.String(50), nullable=False, default='UTC'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('subscription_status', sa.String(20), nullable=False, default='free'),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('daily_requests_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_request_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    
    # Create index on telegram_id for fast lookups
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)
    op.create_index(op.f('ix_users_subscription_status'), 'users', ['subscription_status'])
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'])
    
    # Create children table
    op.create_table(
        'children',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('personality_traits', sa.Text(), nullable=True),
        sa.Column('special_needs', sa.Text(), nullable=True),
        sa.Column('interests', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for children
    op.create_index(op.f('ix_children_parent_id'), 'children', ['parent_id'])
    op.create_index(op.f('ix_children_age'), 'children', ['age'])
    
    # Create family_members table
    op.create_table(
        'family_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('can_view_reports', sa.Boolean(), nullable=False, default=True),
        sa.Column('can_create_translations', sa.Boolean(), nullable=False, default=True),
        sa.Column('can_manage_children', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('telegram_id')
    )
    
    # Create indexes for family_members
    op.create_index(op.f('ix_family_members_user_id'), 'family_members', ['user_id'])
    op.create_index(op.f('ix_family_members_telegram_id'), 'family_members', ['telegram_id'], unique=True)
    
    # Create emotion_translations table
    op.create_table(
        'emotion_translations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('original_message', sa.Text(), nullable=False),
        sa.Column('child_context', sa.Text(), nullable=True),
        sa.Column('situation_context', sa.Text(), nullable=True),
        sa.Column('translated_emotions', sa.JSON(), nullable=True),
        sa.Column('response_options', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('prompt_version', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_id'], ['children.id'], ondelete='SET NULL')
    )
    
    # Create indexes for emotion_translations
    op.create_index(op.f('ix_emotion_translations_user_id'), 'emotion_translations', ['user_id'])
    op.create_index(op.f('ix_emotion_translations_child_id'), 'emotion_translations', ['child_id'])
    op.create_index(op.f('ix_emotion_translations_status'), 'emotion_translations', ['status'])
    op.create_index(op.f('ix_emotion_translations_created_at'), 'emotion_translations', ['created_at'])
    
    # Create checkins table
    op.create_table(
        'checkins',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('checkin_type', sa.String(20), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('response_type', sa.String(20), nullable=False),
        sa.Column('response_metadata', sa.JSON(), nullable=True),
        sa.Column('detected_emotions', sa.JSON(), nullable=True),
        sa.Column('emotion_intensity', sa.JSON(), nullable=True),
        sa.Column('mood_score', sa.Float(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_id'], ['children.id'], ondelete='SET NULL')
    )
    
    # Create indexes for checkins
    op.create_index(op.f('ix_checkins_user_id'), 'checkins', ['user_id'])
    op.create_index(op.f('ix_checkins_child_id'), 'checkins', ['child_id'])
    op.create_index(op.f('ix_checkins_scheduled_at'), 'checkins', ['scheduled_at'])
    op.create_index(op.f('ix_checkins_is_completed'), 'checkins', ['is_completed'])
    op.create_index(op.f('ix_checkins_created_at'), 'checkins', ['created_at'])
    
    # Create weekly_reports table
    op.create_table(
        'weekly_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('week_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('week_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('emotion_trends', sa.JSON(), nullable=False),
        sa.Column('insights', sa.JSON(), nullable=False),
        sa.Column('recommendations', sa.JSON(), nullable=False),
        sa.Column('total_checkins', sa.Integer(), nullable=False, default=0),
        sa.Column('total_translations', sa.Integer(), nullable=False, default=0),
        sa.Column('average_mood_score', sa.Float(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_id'], ['children.id'], ondelete='SET NULL')
    )
    
    # Create indexes for weekly_reports
    op.create_index(op.f('ix_weekly_reports_user_id'), 'weekly_reports', ['user_id'])
    op.create_index(op.f('ix_weekly_reports_child_id'), 'weekly_reports', ['child_id'])
    op.create_index(op.f('ix_weekly_reports_week_start'), 'weekly_reports', ['week_start'])
    op.create_index(op.f('ix_weekly_reports_generated_at'), 'weekly_reports', ['generated_at'])
    
    # Create unique constraint to prevent duplicate reports
    op.create_index(
        'ix_weekly_reports_unique_week',
        'weekly_reports',
        ['user_id', 'child_id', 'week_start'],
        unique=True,
        postgresql_where=sa.text('child_id IS NOT NULL')
    )
    
    # Create unique constraint for user-level reports
    op.create_index(
        'ix_weekly_reports_unique_user_week',
        'weekly_reports',
        ['user_id', 'week_start'],
        unique=True,
        postgresql_where=sa.text('child_id IS NULL')
    )
    
    # Add check constraints
    op.create_check_constraint(
        'ck_users_age_valid',
        'children',
        'age >= 0 AND age <= 18'
    )
    
    op.create_check_constraint(
        'ck_mood_score_range',
        'checkins',
        'mood_score IS NULL OR (mood_score >= -1.0 AND mood_score <= 1.0)'
    )
    
    op.create_check_constraint(
        'ck_confidence_score_range',
        'emotion_translations',
        'confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)'
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('weekly_reports')
    op.drop_table('checkins')
    op.drop_table('emotion_translations')
    op.drop_table('family_members')
    op.drop_table('children')
    op.drop_table('users')