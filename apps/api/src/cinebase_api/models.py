"""Catalog schema (docs/TECHNICAL_SPEC.md §4). Our own UUIDs; provider IDs live in ExternalId."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Kinds of name a film can be found by, best first within a match tier.
NAME_TITLE, NAME_ORIGINAL, NAME_ALTERNATE = 0, 1, 2


class Movie(Timestamps, Base):
    __tablename__ = "movie"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    canonical_title: Mapped[str] = mapped_column(Text)
    original_title: Mapped[str | None] = mapped_column(Text)
    original_language: Mapped[str | None] = mapped_column(String(16))
    # Only a fully known day is stored as a date; an unknown day never becomes January 1.
    release_date: Mapped[date | None] = mapped_column(Date)
    release_year: Mapped[int | None] = mapped_column(SmallInteger)
    release_country: Mapped[str | None] = mapped_column(String(8))
    runtime_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    synopsis: Mapped[str | None] = mapped_column(Text)
    # Short provider description such as "1979 film by Andrei Tarkovsky".
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))  # released | announced | unknown
    kind: Mapped[str] = mapped_column(String(16), server_default="feature")  # feature | short | tv
    # How widely the film is covered (Wikipedia language editions). Not a rating and not user activity.
    notability: Mapped[int] = mapped_column(Integer, server_default="0")
    # Sort keys derived on write.
    title_key: Mapped[str] = mapped_column(Text)
    release_key: Mapped[str | None] = mapped_column(String(10))

    external_ids: Mapped[list["ExternalId"]] = relationship(back_populates="movie", cascade="all, delete-orphan")
    titles: Mapped[list["AlternateTitle"]] = relationship(back_populates="movie", cascade="all, delete-orphan")
    genres: Mapped[list["Genre"]] = relationship(secondary="movie_genre", order_by="Genre.slug")
    credits: Mapped[list["Credit"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan", order_by="Credit.ord"
    )
    assets: Mapped[list["MovieAsset"]] = relationship(back_populates="movie", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_movie_notability", notability.desc(), id),
        Index("ix_movie_title_key", title_key, id),
        Index("ix_movie_release_key", release_key.desc(), title_key, id),
        Index("ix_movie_year", release_year),
        Index("ix_movie_runtime", runtime_minutes),
    )


class ExternalId(Base):
    __tablename__ = "external_id"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("movie.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(Text)

    movie: Mapped[Movie] = relationship(back_populates="external_ids")

    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_external_id_provider"),)


class AlternateTitle(Base):
    """Every name a film is searchable by, including its display and original title (see NAME_*)."""

    __tablename__ = "alternate_title"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("movie.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(Text)
    locale: Mapped[str | None] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(32))
    name_kind: Mapped[int] = mapped_column(SmallInteger, server_default="2")

    movie: Mapped[Movie] = relationship(back_populates="titles")

    __table_args__ = (
        UniqueConstraint("movie_id", "normalized_title", name="uq_alternate_title_movie_norm"),
        Index(
            "ix_alternate_title_norm_pattern", normalized_title, postgresql_ops={"normalized_title": "text_pattern_ops"}
        ),
        Index(
            "ix_alternate_title_norm_trgm",
            normalized_title,
            postgresql_using="gin",
            postgresql_ops={"normalized_title": "gin_trgm_ops"},
        ),
    )


class Genre(Base):
    __tablename__ = "genre"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(Text)


class MovieGenre(Base):
    __tablename__ = "movie_genre"

    movie_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("movie.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genre.id", ondelete="CASCADE"), primary_key=True, index=True)


class Person(Timestamps, Base):
    __tablename__ = "person"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(Text)
    notability: Mapped[int] = mapped_column(Integer, server_default="0")

    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_person_provider"),)


class Credit(Base):
    __tablename__ = "credit"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("movie.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"), index=True)
    department: Mapped[str] = mapped_column(String(32))
    job: Mapped[str] = mapped_column(String(64))
    character: Mapped[str | None] = mapped_column(Text)
    ord: Mapped[int] = mapped_column(SmallInteger)

    movie: Mapped[Movie] = relationship(back_populates="credits")
    person: Mapped[Person] = relationship()


class MovieAsset(Base):
    __tablename__ = "movie_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("movie.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # poster | backdrop
    url: Mapped[str] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32))
    source_kind: Mapped[str] = mapped_column(String(16))  # synthetic | provider | local
    attribution: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    # Page describing the file, its author and license (e.g. the Commons file page).
    source_url: Mapped[str | None] = mapped_column(Text)
    preferred: Mapped[bool] = mapped_column(Boolean, server_default="true")

    movie: Mapped[Movie] = relationship(back_populates="assets")


class ProviderSnapshot(Base):
    """The provider fields last used for a film, so imports can be audited and re-derived."""

    __tablename__ = "provider_snapshot"

    movie_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("movie.id", ondelete="CASCADE"), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Collection(Base):
    __tablename__ = "collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(SmallInteger, server_default="0")


class CollectionItem(Base):
    __tablename__ = "collection_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collection.id", ondelete="CASCADE"))
    movie_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("movie.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)

    __table_args__ = (UniqueConstraint("collection_id", "movie_id", name="uq_collection_item"),)


class CatalogMeta(Base):
    """Key/value facts about the catalog, e.g. its version, which bounds the validity of cursors."""

    __tablename__ = "catalog_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class ImportRun(Base):
    """One CLI import. The checkpoint lets an interrupted run resume where it stopped."""

    __tablename__ = "import_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))  # running | completed | failed
    imported: Mapped[int] = mapped_column(Integer, server_default="0")
    updated: Mapped[int] = mapped_column(Integer, server_default="0")
    failed: Mapped[int] = mapped_column(Integer, server_default="0")
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    error: Mapped[str | None] = mapped_column(Text)
