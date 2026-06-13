"""add_video_sessions

Revision ID: 20260614_add_video_sessions
Revises: 5a1f35890a41
Create Date: 2026-06-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260614_add_video_sessions'
down_revision = '5a1f35890a41'
branch_labels = None
depends_on = None


def upgrade():
    # Создаём таблицу video_sessions
    op.create_table('video_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=True),
        sa.Column('translated_text', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_points', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_sessions_id'), 'video_sessions', ['id'], unique=False)

    # Создаём таблицу video_chat_messages
    op.create_table('video_chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['video_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_chat_messages_id'), 'video_chat_messages', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_video_chat_messages_id'), table_name='video_chat_messages')
    op.drop_table('video_chat_messages')
    op.drop_index(op.f('ix_video_sessions_id'), table_name='video_sessions')
    op.drop_table('video_sessions')