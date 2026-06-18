from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional, Literal


class AccessType(str, Enum):
    SQL = "SQL"
    ORM = "ORM"


class Settings(BaseSettings):
    """Настройки Scrapper сервиса."""

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080

    # Bot service
    BOT_URL: str = "http://bot:8000"

    # GitHub API
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_TOKEN: Optional[SecretStr] = None

    # StackOverflow API
    STACKOVERFLOW_API_URL: str = "https://api.stackexchange.com/2.3"
    # Планировщик
    CHECK_INTERVAL_SECONDS: int = 60
    PARALLEL_WORKERS: int = 1  # количество параллельных обработчиков
    BATCH_SIZE: int = 50
    PREVIEW_MAX_LENGTH: int = 1000

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    HTTP_TIMEOUT: float = 10.0
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_WAIT_MS: int = 1000
    RETRYABLE_STATUSES: list = [429, 500, 502, 503, 504]
    CB_FAILURE_THRESHOLD: int = 5
    CB_RECOVERY_TIMEOUT: int = 30

    RATE_LIMIT_MAX_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    NOTIFICATION_BACKEND: Literal["kafka", "http"] = "http"  # "kafka" или "http"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:29092,kafka-2:29093,kafka-3:29094"
    KAFKA_TOPIC: str = "link.notifications"
    KAFKA_DLQ_TOPIC: str = "link.notifications.dlq"
    KAFKA_RETRIES: int = 3
    KAFKA_ACKNOWLEDGEMENTS: int = 1

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "linktracker"
    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr = SecretStr("123456")
    ACCESS_TYPE: AccessType = AccessType.ORM

    MIN_CHECK_INTERVAL_SECONDS: int = 300

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
