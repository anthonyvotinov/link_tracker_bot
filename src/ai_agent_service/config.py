from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Настройки AI Agent Service."""

    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:29092,kafka-2:29093,kafka-3:29094"
    KAFKA_INPUT_TOPIC: str = "link.raw-updates"
    KAFKA_OUTPUT_TOPIC: str = "link.processed-updates"
    KAFKA_CONSUMER_GROUP: str = "ai-agent-service"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"

    FILTER_STOP_WORDS: List[str] = ["ads", "promo", "buy"]
    FILTER_EXCLUDED_AUTHORS: List[str] = ["bot"]
    FILTER_MIN_LENGTH: int = 20
    SUMMARIZATION_THRESHOLD: int = 333

    PRIORITIZATION_HIGH_KEYWORDS: List[str] = [
        "important",
        "error",
        "crucial",
        "security",
    ]
    PRIORITIZATION_LOW_KEYWORDS: List[str] = ["typo", "docs", "comment"]

    GROUPING_WINDOW_MS: int = 30000

    model_config = SettingsConfigDict(
        env_file="src/data/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
