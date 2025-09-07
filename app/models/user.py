from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    pass


class User(Base):
    """User model."""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="User unique identifier"
    )
    
    # User information
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Hashed password"
    )
    
    role = Column(
        String(10),
        nullable=False,
        default="user",
        comment="User role (user/admin)"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="User creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="User last update timestamp"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'admin')",
            name="users_role_check"
        ),
        CheckConstraint(
            "length(email) > 0",
            name="users_email_not_empty"
        ),
        CheckConstraint(
            "length(password_hash) > 0",
            name="users_password_hash_not_empty"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"
    
    @property
    def is_user(self) -> bool:
        """Check if user is regular user."""
        return self.role == "user"
