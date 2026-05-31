"""add_text_review_and_plagiarism_no_drop

Revision ID: df38ecb424d3
Revises: 0d6840c66531
Create Date: 2026-05-31 01:02:20.971306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'df38ecb424d3'
down_revision: Union[str, None] = '0d6840c66531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Таблица plagiarism_corpus
    if 'plagiarism_corpus' not in tables:
        op.create_table('plagiarism_corpus',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('text_hash', sa.String(length=64), nullable=False),
            sa.Column('shingles', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('text_hash')
        )
        op.create_index(op.f('ix_plagiarism_corpus_id'), 'plagiarism_corpus', ['id'], unique=False)
        op.create_index(op.f('ix_plagiarism_corpus_text_hash'), 'plagiarism_corpus', ['text_hash'], unique=False)
    
    # Таблица text_reviews
    if 'text_reviews' not in tables:
        op.create_table('text_reviews',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(), nullable=True),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('ai_feedback', sa.JSON(), nullable=True),
            sa.Column('plagiarism_percent', sa.Float(), nullable=True),
            sa.Column('similar_parts', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_text_reviews_id'), 'text_reviews', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('text_reviews')
    op.drop_table('plagiarism_corpus')