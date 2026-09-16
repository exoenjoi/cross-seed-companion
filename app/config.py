from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    prowlarr_url: str
    prowlarr_api_key: str
    crossseed_url: str
    crossseed_api_key: str
    crossseed_config_path: Path
    sync_exclude_public: bool = False
    sync_exclude_tag: str | None = None
    docker_manager_url: str | None = None
    actions_config_path: Path | None = None
    crossseed_logs_path: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
