"""catalog schema

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Trigram indexes for fuzzy and substring title search (TECHNICAL_SPEC §3, §6).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "catalog_meta",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "collection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "genre",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "import_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("imported", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "movie",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("canonical_title", sa.Text(), nullable=False),
        sa.Column("original_title", sa.Text(), nullable=True),
        sa.Column("original_language", sa.String(length=16), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("release_year", sa.SmallInteger(), nullable=True),
        sa.Column("release_country", sa.String(length=8), nullable=True),
        sa.Column("runtime_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), server_default="feature", nullable=False),
        sa.Column("notability", sa.Integer(), server_default="0", nullable=False),
        sa.Column("title_key", sa.Text(), nullable=False),
        sa.Column("release_key", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_movie_notability", "movie", [sa.literal_column("notability DESC"), "id"], unique=False)
    op.create_index(
        "ix_movie_release_key",
        "movie",
        [sa.literal_column("release_key DESC"), "title_key", "id"],
        unique=False,
    )
    op.create_index("ix_movie_runtime", "movie", ["runtime_minutes"], unique=False)
    op.create_index("ix_movie_title_key", "movie", ["title_key", "id"], unique=False)
    op.create_index("ix_movie_year", "movie", ["release_year"], unique=False)
    op.create_table(
        "person",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("notability", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_id", name="uq_person_provider"),
    )
    op.create_table(
        "alternate_title",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("name_kind", sa.SmallInteger(), server_default="2", nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movie_id", "normalized_title", name="uq_alternate_title_movie_norm"),
    )
    op.create_index(op.f("ix_alternate_title_movie_id"), "alternate_title", ["movie_id"], unique=False)
    op.create_index(
        "ix_alternate_title_norm_pattern",
        "alternate_title",
        ["normalized_title"],
        unique=False,
        postgresql_ops={"normalized_title": "text_pattern_ops"},
    )
    op.create_index(
        "ix_alternate_title_norm_trgm",
        "alternate_title",
        ["normalized_title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"normalized_title": "gin_trgm_ops"},
    )
    op.create_table(
        "collection_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collection.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "movie_id", name="uq_collection_item"),
    )
    op.create_table(
        "credit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("person_id", sa.UUID(), nullable=False),
        sa.Column("department", sa.String(length=32), nullable=False),
        sa.Column("job", sa.String(length=64), nullable=False),
        sa.Column("character", sa.Text(), nullable=True),
        sa.Column("ord", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_credit_movie_id"), "credit", ["movie_id"], unique=False)
    op.create_index(op.f("ix_credit_person_id"), "credit", ["person_id"], unique=False)
    op.create_table(
        "external_id",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_id", name="uq_external_id_provider"),
    )
    op.create_index(op.f("ix_external_id_movie_id"), "external_id", ["movie_id"], unique=False)
    op.create_table(
        "movie_asset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("preferred", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_movie_asset_movie_id"), "movie_asset", ["movie_id"], unique=False)
    op.create_table(
        "movie_genre",
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("genre_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["genre_id"], ["genre.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("movie_id", "genre_id"),
    )
    op.create_index(op.f("ix_movie_genre_genre_id"), "movie_genre", ["genre_id"], unique=False)
    op.create_table(
        "provider_snapshot",
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("movie_id", "provider"),
    )


def downgrade() -> None:
    op.drop_table("provider_snapshot")
    op.drop_index(op.f("ix_movie_genre_genre_id"), table_name="movie_genre")
    op.drop_table("movie_genre")
    op.drop_index(op.f("ix_movie_asset_movie_id"), table_name="movie_asset")
    op.drop_table("movie_asset")
    op.drop_index(op.f("ix_external_id_movie_id"), table_name="external_id")
    op.drop_table("external_id")
    op.drop_index(op.f("ix_credit_person_id"), table_name="credit")
    op.drop_index(op.f("ix_credit_movie_id"), table_name="credit")
    op.drop_table("credit")
    op.drop_table("collection_item")
    op.drop_index(
        "ix_alternate_title_norm_trgm",
        table_name="alternate_title",
        postgresql_using="gin",
        postgresql_ops={"normalized_title": "gin_trgm_ops"},
    )
    op.drop_index(
        "ix_alternate_title_norm_pattern",
        table_name="alternate_title",
        postgresql_ops={"normalized_title": "text_pattern_ops"},
    )
    op.drop_index(op.f("ix_alternate_title_movie_id"), table_name="alternate_title")
    op.drop_table("alternate_title")
    op.drop_table("person")
    op.drop_index("ix_movie_year", table_name="movie")
    op.drop_index("ix_movie_title_key", table_name="movie")
    op.drop_index("ix_movie_runtime", table_name="movie")
    op.drop_index("ix_movie_release_key", table_name="movie")
    op.drop_index("ix_movie_notability", table_name="movie")
    op.drop_table("movie")
    op.drop_table("import_run")
    op.drop_table("genre")
    op.drop_table("collection")
    op.drop_table("catalog_meta")
