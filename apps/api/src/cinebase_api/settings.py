from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration from the environment (or apps/api/.env). See .env.example."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CINEBASE_", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/cinebase"
    # Identifies this deployment in the Wikimedia User-Agent (their policy asks for a contact URL).
    wikidata_user_agent: str = "CineBase/0.1 (https://github.com/Rokki-Khazratov/CineBase)"
    wikidata_sparql_url: str = "https://query.wikidata.org/sparql"
    commons_api_url: str = "https://commons.wikimedia.org/w/api.php"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
