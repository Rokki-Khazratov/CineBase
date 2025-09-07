"""Initial migration for SQLite

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(10), nullable=False, default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("role IN ('user', 'admin')", name='users_role_check'),
        sa.CheckConstraint('length(email) > 0', name='users_email_not_empty'),
        sa.CheckConstraint('length(password_hash) > 0', name='users_password_hash_not_empty')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create movies table
    op.create_table('movies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('genres', sa.Text(), nullable=True),  # JSON string for SQLite
        sa.Column('overview', sa.Text(), nullable=True),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('custom_poster_path', sa.String(500), nullable=True),
        sa.Column('custom_trailer_url', sa.String(500), nullable=True),
        sa.Column('tmdb_snapshot', sa.Text(), nullable=True),  # JSON string for SQLite
        sa.Column('tmdb_snapshot_updated', sa.DateTime(), nullable=True),
        sa.Column('is_custom', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('year IS NULL OR (year >= 1888 AND year <= 2030)', name='movies_year_range_check'),
        sa.CheckConstraint('title IS NULL OR length(title) > 0', name='movies_title_not_empty'),
        sa.CheckConstraint('title IS NULL OR length(title) <= 255', name='movies_title_length_check'),
        sa.CheckConstraint('tmdb_id IS NOT NULL OR is_custom = 1', name='movies_tmdb_or_custom_check')
    )
    op.create_index(op.f('ix_movies_id'), 'movies', ['id'], unique=False)
    op.create_index(op.f('ix_movies_title'), 'movies', ['title'], unique=False)
    op.create_index(op.f('ix_movies_year'), 'movies', ['year'], unique=False)
    op.create_index(op.f('ix_movies_tmdb_id'), 'movies', ['tmdb_id'], unique=True)


def downgrade() -> None:
    # Drop tables
    op.drop_table('movies')
    op.drop_table('users')
