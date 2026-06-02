"""add_vacancies_and_applications_manual

Revision ID: c53969bfd770
Revises: 3936df677996
Create Date: 2026-06-02 13:08:33.808250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c53969bfd770'
down_revision: Union[str, None] = '3936df677996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём таблицу companies
    op.create_table('companies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)

    # Создаём таблицу vacancies
    op.create_table('vacancies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('experience_years', sa.Float(), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('employment_type', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vacancies_id'), 'vacancies', ['id'], unique=False)

    # Создаём таблицу user_vacancies
    op.create_table('user_vacancies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vacancy_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('matching_score', sa.Float(), nullable=True),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vacancy_id'], ['vacancies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_vacancies_id'), 'user_vacancies', ['id'], unique=False)

    # Добавляем новые столбцы в таблицу users
    op.add_column('users', sa.Column('cv_summary', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('desired_position', sa.String(), nullable=True))
    op.add_column('users', sa.Column('desired_salary', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('work_experience_years', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('github_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('linkedin_url', sa.String(), nullable=True))


def downgrade() -> None:
    # Удаляем добавленные столбцы
    op.drop_column('users', 'linkedin_url')
    op.drop_column('users', 'github_url')
    op.drop_column('users', 'work_experience_years')
    op.drop_column('users', 'desired_salary')
    op.drop_column('users', 'desired_position')
    op.drop_column('users', 'cv_summary')
    
    # Удаляем таблицы в обратном порядке
    op.drop_index(op.f('ix_user_vacancies_id'), table_name='user_vacancies')
    op.drop_table('user_vacancies')
    op.drop_index(op.f('ix_vacancies_id'), table_name='vacancies')
    op.drop_table('vacancies')
    op.drop_index(op.f('ix_companies_id'), table_name='companies')
    op.drop_table('companies')