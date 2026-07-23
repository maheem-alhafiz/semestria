"""
Centralized application configuration.

All environment-dependent values live here and nowhere else, so the rest of
the codebase never touches os.environ directly. Values are loaded from a
.env file in local development and from real environment variables in
staging/production.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    # --- Database ---
    database_url: str = "postgresql+psycopg2://planner:planner@localhost:5432/planner"

    # --- Aurora Importer (used starting Phase 3) ---
    aurora_base_url: str = "https://aurora-registration.umanitoba.ca/StudentRegistrationSsb/ssb"
    aurora_request_delay_seconds: float = 0.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so the .env file is only parsed once per process."""
    return Settings()
