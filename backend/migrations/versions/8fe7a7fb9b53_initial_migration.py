"""initial_migration

Revision ID: 8fe7a7fb9b53
Revises: 
Create Date: 2026-06-01 02:25:38.510228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8fe7a7fb9b53'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== 1. Базовые таблицы без внешних зависимостей ==========
    op.create_table('users',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('username', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('hashed_password', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('full_name', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('is_verified', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('last_login', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('avatar_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('bio', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('country', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('city', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('timezone', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('language', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('total_xp', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('level', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('current_hsk_level', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('target_hsk_level', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('exam_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('daily_goal', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('total_points', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('study_streak', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('longest_streak', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('last_activity_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('total_study_time', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('total_words_learned', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('total_tests_taken', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('average_test_score', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('email_notifications', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('theme', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('education_background', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('university_target', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('program_target', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('department_target', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('work_experience', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('projects', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('languages', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('technical_skills', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('achievements_text', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('letter_style', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('users_pkey'))
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table('roles',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('display_name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('is_default', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('can_be_assigned_by_user', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('requires_approval', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('roles_pkey')),
        sa.UniqueConstraint('name', name=op.f('roles_name_key'))
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)

    op.create_table('user_roles',
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('role_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('user_roles_role_id_fkey'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_roles_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('user_roles_pkey'))
    )

    # ========== 2. Таблицы, зависящие от users ==========
    op.create_table('syllabus_courses',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('department', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('university', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('semester', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('credits', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('total_hours', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('competencies', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('syllabus_content', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('assessment_tools', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('literature', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('syllabus_courses_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('syllabus_courses_pkey'))
    )
    op.create_index(op.f('ix_syllabus_courses_id'), 'syllabus_courses', ['id'], unique=False)

    op.create_table('schools',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('owner_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('invite_code', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('schools_owner_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('schools_pkey')),
        sa.UniqueConstraint('invite_code', name=op.f('schools_invite_code_key'))
    )
    op.create_index(op.f('ix_schools_id'), 'schools', ['id'], unique=False)

    op.create_table('text_reviews',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('text', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('ai_feedback', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('plagiarism_percent', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('similar_parts', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('text_reviews_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('text_reviews_pkey'))
    )
    op.create_index(op.f('ix_text_reviews_id'), 'text_reviews', ['id'], unique=False)

    op.create_table('api_keys',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('key', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('permissions', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('rate_limit_per_minute', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('last_used_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('api_keys_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('api_keys_pkey'))
    )
    op.create_index(op.f('ix_api_keys_key'), 'api_keys', ['key'], unique=True)
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)

    op.create_table('tasks',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('deadline', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('reminder_sent', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('tasks_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('tasks_pkey'))
    )
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)

    op.create_table('user_performances',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('topic', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('correct_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('total_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('last_attempt', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('mastery_level', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('total_time_spent', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_performances_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('user_performances_pkey'))
    )
    op.create_index(op.f('ix_user_performances_id'), 'user_performances', ['id'], unique=False)

    op.create_table('custom_tests',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('questions', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('custom_tests_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('custom_tests_pkey'))
    )
    op.create_index(op.f('ix_custom_tests_id'), 'custom_tests', ['id'], unique=False)

    op.create_table('user_courses',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('success_criteria', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_courses_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('user_courses_pkey'))
    )
    op.create_index(op.f('ix_user_courses_id'), 'user_courses', ['id'], unique=False)

    op.create_table('user_lessons',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('subject', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('content', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('success_criteria', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('youtube_urls', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('presentation_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_lessons_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('user_lessons_pkey'))
    )
    op.create_index(op.f('ix_user_lessons_id'), 'user_lessons', ['id'], unique=False)

    op.create_table('sessions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('exam_name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('exam_details', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('target_profile', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('current_profile', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('time_available_days', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('study_plan', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('sessions_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('sessions_pkey'))
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)

    op.create_table('password_resets',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('token', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column('used', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('used_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('password_resets_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('password_resets_pkey'))
    )
    op.create_index(op.f('ix_password_resets_token'), 'password_resets', ['token'], unique=True)
    op.create_index(op.f('ix_password_resets_id'), 'password_resets', ['id'], unique=False)

    op.create_table('refresh_tokens',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('token', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('device_info', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('ip_address', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('refresh_tokens_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('refresh_tokens_pkey'))
    )
    op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_id'), 'refresh_tokens', ['id'], unique=False)

    op.create_table('user_auth',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('username', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('password_hash', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('avatar_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('last_login', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_auth_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('user_auth_pkey')),
        sa.UniqueConstraint('user_id', name=op.f('user_auth_user_id_key'))
    )
    op.create_index(op.f('ix_user_auth_username'), 'user_auth', ['username'], unique=True)
    op.create_index(op.f('ix_user_auth_id'), 'user_auth', ['id'], unique=False)

    op.create_table('user_actions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('action_type', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('action_data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('ip_address', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('user_agent', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('method', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('duration_ms', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('module_name', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_actions_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('user_actions_pkey'))
    )
    op.create_index(op.f('ix_user_actions_user_timestamp'), 'user_actions', ['user_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_user_actions_user_id'), 'user_actions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_actions_timestamp'), 'user_actions', ['timestamp'], unique=False)
    op.create_index(op.f('ix_user_actions_id'), 'user_actions', ['id'], unique=False)
    op.create_index(op.f('ix_user_actions_action_type'), 'user_actions', ['action_type'], unique=False)

    op.create_table('chat_messages',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('thread_id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('role', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('content', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('message_metadata', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('chat_messages_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('chat_messages_pkey'))
    )
    op.create_index(op.f('ix_chat_messages_thread_id'), 'chat_messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)

    # ========== 3. Таблицы, зависящие от sessions, schools и т.д. ==========
    op.create_table('course_modules',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('order', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['user_courses.id'], name=op.f('course_modules_course_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('course_modules_pkey'))
    )
    op.create_index(op.f('ix_course_modules_id'), 'course_modules', ['id'], unique=False)

    op.create_table('course_lessons',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('module_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('order', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('content', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('homework', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('success_criteria', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('youtube_urls', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('presentation_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['course_modules.id'], name=op.f('course_lessons_module_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('course_lessons_pkey'))
    )
    op.create_index(op.f('ix_course_lessons_id'), 'course_lessons', ['id'], unique=False)

    op.create_table('lessons',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('topic', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('content', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('tasks', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('completed', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('score', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('completed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('time_spent_seconds', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('task_times', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('lessons_session_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('lessons_pkey'))
    )
    op.create_index(op.f('ix_lessons_id'), 'lessons', ['id'], unique=False)

    op.create_table('lesson_videos',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('lesson_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('video_path', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('generated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], name=op.f('lesson_videos_lesson_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('lesson_videos_pkey')),
        sa.UniqueConstraint('lesson_id', name=op.f('lesson_videos_lesson_id_key'))
    )
    op.create_index(op.f('ix_lesson_videos_id'), 'lesson_videos', ['id'], unique=False)

    op.create_table('test_results',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('test_type', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('questions', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('answers', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('evaluation', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('score', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('time_spent_seconds', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('question_times', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('test_results_session_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('test_results_pkey'))
    )
    op.create_index(op.f('ix_test_results_id'), 'test_results', ['id'], unique=False)

    op.create_table('progress_history',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('profile_snapshot', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('progress_history_session_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('progress_history_pkey'))
    )
    op.create_index(op.f('ix_progress_history_id'), 'progress_history', ['id'], unique=False)

    op.create_table('user_interactions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('session_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('interaction_type', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('topic', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('user_input', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('ai_response', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('feedback_score', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('user_interactions_session_id_fkey'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_interactions_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('user_interactions_pkey'))
    )
    op.create_index(op.f('ix_user_interactions_id'), 'user_interactions', ['id'], unique=False)

    op.create_table('data_analysis_sessions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('filename', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('file_path', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('dataframe_json', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('code', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('output_text', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('output_images', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('error_message', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('data_analysis_sessions_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('data_analysis_sessions_pkey'))
    )
    op.create_index(op.f('ix_data_analysis_sessions_id'), 'data_analysis_sessions', ['id'], unique=False)

    op.create_table('topic_time_stats',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('topic', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('total_seconds', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('sessions_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('last_updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('topic_time_stats_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('topic_time_stats_pkey'))
    )
    op.create_index(op.f('ix_topic_time_stats_id'), 'topic_time_stats', ['id'], unique=False)

    op.create_table('study_sessions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('start_time', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('end_time', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('duration_minutes', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('actions_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('words_studied', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('tests_taken', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('study_sessions_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('study_sessions_pkey'))
    )
    op.create_index(op.f('ix_study_sessions_id'), 'study_sessions', ['id'], unique=False)

    op.create_table('user_documents',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('filename', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('original_filename', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('file_path', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('index_path', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('chunks_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_documents_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('user_documents_pkey'))
    )
    op.create_index(op.f('ix_user_documents_id'), 'user_documents', ['id'], unique=False)

    op.create_table('school_members',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('role', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('joined_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], name=op.f('school_members_school_id_fkey'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('school_members_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('school_members_pkey'))
    )
    op.create_index(op.f('ix_school_members_id'), 'school_members', ['id'], unique=False)

    op.create_table('school_chat_messages',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('message', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('is_private', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('recipient_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], name=op.f('school_chat_messages_recipient_id_fkey'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], name=op.f('school_chat_messages_school_id_fkey'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('school_chat_messages_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('school_chat_messages_pkey'))
    )
    op.create_index(op.f('ix_school_chat_messages_id'), 'school_chat_messages', ['id'], unique=False)

    op.create_table('exam_tickets',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('course_name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('num_questions', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('ticket_type', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('questions', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('exam_tickets_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('exam_tickets_pkey'))
    )
    op.create_index(op.f('ix_exam_tickets_id'), 'exam_tickets', ['id'], unique=False)

    op.create_table('admin_logs',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('admin_user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('target_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('action', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], name=op.f('admin_logs_admin_user_id_fkey')),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], name=op.f('admin_logs_target_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('admin_logs_pkey'))
    )
    op.create_index(op.f('ix_admin_logs_id'), 'admin_logs', ['id'], unique=False)

    op.create_table('scientific_articles',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('arxiv_id', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('authors', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('summary', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('published', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('bibtex', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('is_favorite', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('scientific_articles_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('scientific_articles_pkey'))
    )
    op.create_index(op.f('ix_scientific_articles_id'), 'scientific_articles', ['id'], unique=False)

    op.create_table('student_performances',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('school_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('target_graph', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('current_graph', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('topics_progress', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('total_time_spent', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('average_score', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('last_updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], name=op.f('student_performances_school_id_fkey'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('student_performances_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('student_performances_pkey'))
    )
    op.create_index(op.f('ix_student_performances_id'), 'student_performances', ['id'], unique=False)

    op.create_table('interview_sessions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('university', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('program', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('degree', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('professors', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('tech_expert', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('messages', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('ended', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('interview_sessions_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('interview_sessions_pkey'))
    )
    op.create_index(op.f('ix_interview_sessions_session_id'), 'interview_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_interview_sessions_id'), 'interview_sessions', ['id'], unique=False)

    op.create_table('ielts_attempts',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('task_type', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('audio_path', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('transcript', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('answer_text', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('scores', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('overall_band', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('feedback', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('suggestions', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('ielts_attempts_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('ielts_attempts_pkey'))
    )
    op.create_index(op.f('ix_ielts_attempts_id'), 'ielts_attempts', ['id'], unique=False)

    op.create_table('grammar_topics',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('topic_id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name_zh', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name_en', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name_ru', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('level', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('category', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('explanation', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('examples', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('grammar_topics_pkey'))
    )
    op.create_index(op.f('ix_grammar_topics_topic_id'), 'grammar_topics', ['topic_id'], unique=True)
    op.create_index(op.f('ix_grammar_topics_id'), 'grammar_topics', ['id'], unique=False)

    op.create_table('plagiarism_corpus',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('text_hash', sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        sa.Column('shingles', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('plagiarism_corpus_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('plagiarism_corpus_pkey'))
    )
    op.create_index(op.f('ix_plagiarism_corpus_text_hash'), 'plagiarism_corpus', ['text_hash'], unique=True)
    op.create_index(op.f('ix_plagiarism_corpus_id'), 'plagiarism_corpus', ['id'], unique=False)

    op.create_table('csca_topics',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('topic_id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name_zh', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name_en', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('subject', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('difficulty', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('order', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('csca_topics_pkey'))
    )
    op.create_index(op.f('ix_csca_topics_topic_id'), 'csca_topics', ['topic_id'], unique=True)
    op.create_index(op.f('ix_csca_topics_id'), 'csca_topics', ['id'], unique=False)

    op.create_table('user_achievements',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('achievement_type', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('module_name', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('xp_awarded', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_achievements_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('user_achievements_pkey'))
    )
    op.create_index(op.f('ix_user_achievements_id'), 'user_achievements', ['id'], unique=False)

    op.create_table('user_tests',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('test_id', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('test_type', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('test_level', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('score', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('max_score', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('percentage', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('time_spent', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('questions_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('correct_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('wrong_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('skipped_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('answers', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('results', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_tests_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('user_tests_pkey'))
    )
    op.create_index(op.f('ix_user_tests_id'), 'user_tests', ['id'], unique=False)

    op.create_table('universities',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name_zh', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name_en', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('city', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('province', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('ranking', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('type', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('website', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('tuition_cny', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('scholarships', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('programs', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('universities_pkey'))
    )
    op.create_index(op.f('ix_universities_id'), 'universities', ['id'], unique=False)

    op.create_table('hsk_words',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('character', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('pinyin', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('translation_ru', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('translation_en', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('hsk_level', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('part_of_speech', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('example', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('example_translation', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('hsk_words_pkey'))
    )
    op.create_index(op.f('ix_hsk_words_id'), 'hsk_words', ['id'], unique=False)

    op.create_table('user_words',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('word_id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('word_text', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('hsk_level', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('difficulty', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('views_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('practice_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('correct_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('wrong_count', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('last_viewed', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('last_practiced', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_words_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('user_words_pkey'))
    )
    op.create_index(op.f('ix_user_words_user_word'), 'user_words', ['user_id', 'word_id'], unique=True)
    op.create_index(op.f('ix_user_words_id'), 'user_words', ['id'], unique=False)


def downgrade() -> None:
    # Удаление в обратном порядке (сперва таблицы с внешними ключами, потом базовые)
    op.drop_index(op.f('ix_user_words_user_word'), table_name='user_words')
    op.drop_index(op.f('ix_user_words_id'), table_name='user_words')
    op.drop_table('user_words')
    op.drop_index(op.f('ix_hsk_words_id'), table_name='hsk_words')
    op.drop_table('hsk_words')
    op.drop_index(op.f('ix_universities_id'), table_name='universities')
    op.drop_table('universities')
    op.drop_index(op.f('ix_user_tests_id'), table_name='user_tests')
    op.drop_table('user_tests')
    op.drop_index(op.f('ix_user_achievements_id'), table_name='user_achievements')
    op.drop_table('user_achievements')
    op.drop_index(op.f('ix_csca_topics_topic_id'), table_name='csca_topics')
    op.drop_index(op.f('ix_csca_topics_id'), table_name='csca_topics')
    op.drop_table('csca_topics')
    op.drop_index(op.f('ix_plagiarism_corpus_text_hash'), table_name='plagiarism_corpus')
    op.drop_index(op.f('ix_plagiarism_corpus_id'), table_name='plagiarism_corpus')
    op.drop_table('plagiarism_corpus')
    op.drop_index(op.f('ix_grammar_topics_topic_id'), table_name='grammar_topics')
    op.drop_index(op.f('ix_grammar_topics_id'), table_name='grammar_topics')
    op.drop_table('grammar_topics')
    op.drop_index(op.f('ix_ielts_attempts_id'), table_name='ielts_attempts')
    op.drop_table('ielts_attempts')
    op.drop_index(op.f('ix_interview_sessions_session_id'), table_name='interview_sessions')
    op.drop_index(op.f('ix_interview_sessions_id'), table_name='interview_sessions')
    op.drop_table('interview_sessions')
    op.drop_index(op.f('ix_student_performances_id'), table_name='student_performances')
    op.drop_table('student_performances')
    op.drop_index(op.f('ix_scientific_articles_id'), table_name='scientific_articles')
    op.drop_table('scientific_articles')
    op.drop_index(op.f('ix_admin_logs_id'), table_name='admin_logs')
    op.drop_table('admin_logs')
    op.drop_index(op.f('ix_exam_tickets_id'), table_name='exam_tickets')
    op.drop_table('exam_tickets')
    op.drop_index(op.f('ix_school_chat_messages_id'), table_name='school_chat_messages')
    op.drop_table('school_chat_messages')
    op.drop_index(op.f('ix_school_members_id'), table_name='school_members')
    op.drop_table('school_members')
    op.drop_index(op.f('ix_user_documents_id'), table_name='user_documents')
    op.drop_table('user_documents')
    op.drop_index(op.f('ix_study_sessions_id'), table_name='study_sessions')
    op.drop_table('study_sessions')
    op.drop_index(op.f('ix_topic_time_stats_id'), table_name='topic_time_stats')
    op.drop_table('topic_time_stats')
    op.drop_index(op.f('ix_data_analysis_sessions_id'), table_name='data_analysis_sessions')
    op.drop_table('data_analysis_sessions')
    op.drop_index(op.f('ix_user_interactions_id'), table_name='user_interactions')
    op.drop_table('user_interactions')
    op.drop_index(op.f('ix_progress_history_id'), table_name='progress_history')
    op.drop_table('progress_history')
    op.drop_index(op.f('ix_test_results_id'), table_name='test_results')
    op.drop_table('test_results')
    op.drop_index(op.f('ix_lesson_videos_id'), table_name='lesson_videos')
    op.drop_table('lesson_videos')
    op.drop_index(op.f('ix_lessons_id'), table_name='lessons')
    op.drop_table('lessons')
    op.drop_index(op.f('ix_course_lessons_id'), table_name='course_lessons')
    op.drop_table('course_lessons')
    op.drop_index(op.f('ix_course_modules_id'), table_name='course_modules')
    op.drop_table('course_modules')
    op.drop_index(op.f('ix_chat_messages_thread_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_user_actions_user_timestamp'), table_name='user_actions')
    op.drop_index(op.f('ix_user_actions_user_id'), table_name='user_actions')
    op.drop_index(op.f('ix_user_actions_timestamp'), table_name='user_actions')
    op.drop_index(op.f('ix_user_actions_id'), table_name='user_actions')
    op.drop_index(op.f('ix_user_actions_action_type'), table_name='user_actions')
    op.drop_table('user_actions')
    op.drop_index(op.f('ix_user_auth_username'), table_name='user_auth')
    op.drop_index(op.f('ix_user_auth_id'), table_name='user_auth')
    op.drop_table('user_auth')
    op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(op.f('ix_password_resets_token'), table_name='password_resets')
    op.drop_index(op.f('ix_password_resets_id'), table_name='password_resets')
    op.drop_table('password_resets')
    op.drop_index(op.f('ix_sessions_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_user_lessons_id'), table_name='user_lessons')
    op.drop_table('user_lessons')
    op.drop_index(op.f('ix_user_courses_id'), table_name='user_courses')
    op.drop_table('user_courses')
    op.drop_index(op.f('ix_custom_tests_id'), table_name='custom_tests')
    op.drop_table('custom_tests')
    op.drop_index(op.f('ix_user_performances_id'), table_name='user_performances')
    op.drop_table('user_performances')
    op.drop_index(op.f('ix_tasks_id'), table_name='tasks')
    op.drop_table('tasks')
    op.drop_index(op.f('ix_api_keys_key'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index(op.f('ix_text_reviews_id'), table_name='text_reviews')
    op.drop_table('text_reviews')
    op.drop_index(op.f('ix_schools_id'), table_name='schools')
    op.drop_table('schools')
    op.drop_index(op.f('ix_syllabus_courses_id'), table_name='syllabus_courses')
    op.drop_table('syllabus_courses')
    op.drop_table('user_roles')
    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_table('roles')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')