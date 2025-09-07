from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSON
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Movie(Base):
    """Movie model with TMDB integration."""
    
    __tablename__ = "movies"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Movie unique identifier"
    )
    
    # TMDB integration
    tmdb_id = Column(
        Integer,
        nullable=True,
        unique=True,
        index=True,
        comment="TMDB movie ID"
    )
    
    # Movie information (local overrides)
    title = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Custom movie title (overrides TMDB)"
    )
    
    year = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Custom release year (overrides TMDB)"
    )
    
    genres = Column(
        ARRAY(String),
        nullable=True,
        comment="Custom genres (overrides TMDB)"
    )
    
    overview = Column(
        Text,
        nullable=True,
        comment="Custom overview (overrides TMDB)"
    )
    
    # Custom assets
    custom_poster_path = Column(
        String(500),
        nullable=True,
        comment="Path to custom poster"
    )
    
    custom_trailer_url = Column(
        String(500),
        nullable=True,
        comment="Custom trailer URL"
    )
    
    # TMDB snapshot (cached data)
    tmdb_snapshot = Column(
        JSON,
        nullable=True,
        comment="Cached TMDB data"
    )
    
    tmdb_snapshot_updated = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last TMDB snapshot update"
    )
    
    # Metadata
    is_custom = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Is this a custom movie (not from TMDB)"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="Movie creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="Movie last update timestamp"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "year IS NULL OR (year >= 1888 AND year <= 2030)",
            name="movies_year_range_check"
        ),
        CheckConstraint(
            "title IS NULL OR length(title) > 0",
            name="movies_title_not_empty"
        ),
        CheckConstraint(
            "title IS NULL OR length(title) <= 255",
            name="movies_title_length_check"
        ),
        CheckConstraint(
            "tmdb_id IS NOT NULL OR is_custom = true",
            name="movies_tmdb_or_custom_check"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Movie(id={self.id}, title={self.title}, tmdb_id={self.tmdb_id})>"
    
    @property
    def genres_list(self) -> list[str]:
        """Get genres as list."""
        return self.genres or []
    
    def has_genre(self, genre: str) -> bool:
        """Check if movie has specific genre."""
        return genre.lower() in [g.lower() for g in self.genres_list]
    
    @property
    def display_title(self) -> str:
        """Get display title (custom or from TMDB)."""
        if self.title:
            return self.title
        if self.tmdb_snapshot and "title" in self.tmdb_snapshot:
            return self.tmdb_snapshot["title"]
        return "Unknown Title"
    
    @property
    def display_year(self) -> int | None:
        """Get display year (custom or from TMDB)."""
        if self.year:
            return self.year
        if self.tmdb_snapshot and "release_date" in self.tmdb_snapshot:
            try:
                return int(self.tmdb_snapshot["release_date"][:4])
            except (ValueError, TypeError):
                pass
        return None
    
    @property
    def display_overview(self) -> str:
        """Get display overview (custom or from TMDB)."""
        if self.overview:
            return self.overview
        if self.tmdb_snapshot and "overview" in self.tmdb_snapshot:
            return self.tmdb_snapshot["overview"]
        return ""
    
    @property
    def display_genres(self) -> list[str]:
        """Get display genres (custom or from TMDB)."""
        if self.genres:
            return self.genres
        if self.tmdb_snapshot and "genres" in self.tmdb_snapshot:
            return [genre["name"] for genre in self.tmdb_snapshot["genres"]]
        return []
    
    @property
    def poster_url(self) -> str | None:
        """Get poster URL (custom or from TMDB)."""
        if self.custom_poster_path:
            return f"/media/posters/{self.custom_poster_path}"
        if self.tmdb_snapshot and "poster_path" in self.tmdb_snapshot:
            return f"https://image.tmdb.org/t/p/w500{self.tmdb_snapshot['poster_path']}"
        return None
