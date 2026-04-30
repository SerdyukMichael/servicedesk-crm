from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    app_name: str = "ServiceDesk CRM"
    debug: bool = False
    enable_docs: bool = False  # Swagger/ReDoc — только при явном ENABLE_DOCS=true
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
    # CORS: укажите реальный домен фронтенда в .env, например:
    # ALLOWED_ORIGINS=https://crm.example.com
    # Для локальной разработки: ALLOWED_ORIGINS=http://localhost,http://localhost:5173
    allowed_origins: List[str] = ["http://localhost", "http://localhost:5173", "http://localhost:80"]

    class Config:
        env_file = ".env"
        extra = "ignore"  # игнорировать MYSQL_* и прочие Docker-переменные


settings = Settings()
