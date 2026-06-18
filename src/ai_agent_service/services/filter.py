from src.ai_agent_service.config import settings
from src.ai_agent_service.models import RawUpdate


class UpdateFilter:
    """Фильтрация обновлений по стоп-словам, авторам и длине."""

    def __init__(self):
        self.stop_words = [w.lower() for w in settings.FILTER_STOP_WORDS]
        self.excluded_authors = [a.lower() for a in settings.FILTER_EXCLUDED_AUTHORS]
        self.min_length = settings.FILTER_MIN_LENGTH

    def should_skip(self, update: RawUpdate) -> bool:
        """Возвращает True, если обновление нужно пропустить."""

        if len(update.description) < self.min_length:
            return True

        if update.author.lower() in self.excluded_authors:
            return True

        text_lower = update.description.lower()
        if any(word in text_lower for word in self.stop_words):
            return True

        return False
