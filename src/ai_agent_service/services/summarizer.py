from src.ai_agent_service.config import settings


class Summarizer:
    """Суммаризация длинных текстов (заглушкa)."""

    def __init__(self):
        self.threshold = settings.SUMMARIZATION_THRESHOLD

    def summarize(self, text: str) -> str:
        """Сокращает текст, если он превышает порог."""
        if len(text) <= self.threshold:
            return text

        return text[: self.threshold].rstrip() + "..."
