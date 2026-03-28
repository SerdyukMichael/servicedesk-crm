from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "ServiceDesk CRM"
    debug: bool = False
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    redis_url: str = "redis://redis:6379/0"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    max_file_size_mb: int = 20

    class Config:
        env_file = ".env"
        extra = "ignore"  # игнорировать MYSQL_* и прочие Docker-переменные


settings = Settings()
