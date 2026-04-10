from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "SoC Dashboard API"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://soc:soc_secret@localhost:5432/soc_dashboard"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: str = '["http://localhost:3000"]'

    # Data paths
    parquet_dir: str = "/data/parquet"
    reports_dir: str = "/data/reports"

    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@soc-dashboard.local"

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)


settings = Settings()
