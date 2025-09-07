from __future__ import annotations

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    app_name: str = Field(default="CineBase", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_env: str = Field(default="dev", description="Environment (dev/prod)")
    app_host: str = Field(default="0.0.0.0", description="Host to bind to")
    app_port: int = Field(default=8000, description="Port to bind to")
    
    # Security
    secret_key: str = Field(..., description="Secret key for JWT tokens")
    access_token_expire_minutes: int = Field(default=15, description="JWT token expiration in minutes")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./cinebase.db", description="Database connection URL")
    
    # Cache
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # TMDB API
    tmdb_api_key: str = Field(default="", description="TMDB API key")
    tmdb_base_url: str = Field(default="https://api.themoviedb.org/3", description="TMDB API base URL")
    tmdb_image_base_url: str = Field(default="https://image.tmdb.org/t/p", description="TMDB image base URL")
    
    # Media storage
    media_dir: str = Field(default="./media", description="Media files directory")
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Max file size in bytes (10MB)")
    allowed_image_types: list[str] = Field(default=["image/jpeg", "image/png", "image/webp"], description="Allowed image MIME types")
    
    # CORS
    cors_origins: str = Field(default="*", description="CORS allowed origins (comma-separated)")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Development
    debug: bool = Field(default=False, description="Debug mode")
    reload: bool = Field(default=False, description="Auto-reload on changes")
    gitpus
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Environment variable mapping
        fields = {
            "app_name": {"env": "APP_NAME"},
            "app_version": {"env": "APP_VERSION"},
            "app_env": {"env": "APP_ENV"},
            "app_host": {"env": "APP_HOST"},
            "app_port": {"env": "APP_PORT"},
            "secret_key": {"env": "SECRET_KEY"},
            "access_token_expire_minutes": {"env": "ACCESS_TOKEN_EXPIRE_MINUTES"},
            "algorithm": {"env": "ALGORITHM"},
            "database_url": {"env": "DATABASE_URL"},
            "redis_url": {"env": "REDIS_URL"},
            "tmdb_api_key": {"env": "TMDB_API_KEY"},
            "tmdb_base_url": {"env": "TMDB_BASE_URL"},
            "tmdb_image_base_url": {"env": "TMDB_IMAGE_BASE_URL"},
            "media_dir": {"env": "MEDIA_DIR"},
            "max_file_size": {"env": "MAX_FILE_SIZE"},
            "cors_origins": {"env": "CORS_ORIGINS"},
            "log_level": {"env": "LOG_LEVEL"},
            "debug": {"env": "DEBUG"},
            "reload": {"env": "RELOAD"},
        }
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "prod"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env == "dev"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
