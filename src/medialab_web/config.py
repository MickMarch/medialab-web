from pydantic_settings import BaseSettings, SettingsConfigDict

from medialab_web.constants import DEFAULT_SESSION_MAX_AGE_SECONDS


class AppConfig(BaseSettings):
    """Every field is optional at import time (CI has no .env); startup checks
    the ones that must be set."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    orchestrator_url: str = "http://medialab-orchestrator:8000"
    orchestrator_api_key: str = ""
    web_password: str | None = None
    web_secret_key: str | None = None
    session_max_age_seconds: int = DEFAULT_SESSION_MAX_AGE_SECONDS
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    gateway_timeout_seconds: float = 30.0
    log_level: str = "INFO"


config = AppConfig()
