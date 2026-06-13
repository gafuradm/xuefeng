"""add_admission_mentor

Revision ID: 5d0d5a42a7c0
Revises: 20260614_add_video_sessions
Create Date: 2026-06-14 05:29:08.017284

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5d0d5a42a7c0'
down_revision = '20260614_add_video_sessions'
branch_labels = None
depends_on = None


def upgrade():
    # Создаём таблицу admission_profiles
    op.create_table('admission_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('user_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admission_profiles_id'), 'admission_profiles', ['id'], unique=False)

    # Создаём таблицу admission_results
    op.create_table('admission_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('university_name', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('contact_email', sa.String(), nullable=True),
        sa.Column('ranking', sa.Integer(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=False),
        sa.Column('admission_chance', sa.Float(), nullable=False),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('gaps', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('action_plan', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['admission_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admission_results_id'), 'admission_results', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_admission_results_id'), table_name='admission_results')
    op.drop_table('admission_results')
    op.drop_index(op.f('ix_admission_profiles_id'), table_name='admission_profiles')
    op.drop_table('admission_profiles')