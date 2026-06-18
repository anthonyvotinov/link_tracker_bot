from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    BOT_TOKEN: str
    PROXY: str
    BOT_NAME: str = "LinkTracker Bot"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    SCRAPPER_URL: str = "http://localhost:8080"

    MESSAGE_SOURCE: Literal["kafka", "http"] = "http"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:29092,kafka-2:29093,kafka-3:29094"
    KAFKA_TOPIC: str = "link.processed-updates"
    KAFKA_CONSUMER_GROUP: str = "bot-service-consumers"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"

    HTTP_TIMEOUT: float = 10.0
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_WAIT_MS: int = 1000
    RETRYABLE_STATUSES: str = "429,500,502,503,504"
    CB_FAILURE_THRESHOLD: int = 5
    CB_RECOVERY_TIMEOUT: int = 30
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file="src/data/.env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings(
    BOT_TOKEN="7839300611:AAEF3Ak9Qfh2-ao_VWcGuM_PktrmckyNEPw",
    PROXY="https://telegram-api-proxy.antontracker.workers.dev",
)
