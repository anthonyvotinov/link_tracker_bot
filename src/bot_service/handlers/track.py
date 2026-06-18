from enum import Enum, auto
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from src.bot_service.clients.scrapper_client import scrapper_client
from ai_agent_service.logger import logger
from src.bot_service.tools import get_user_data, get_update_fields


class TrackState(Enum):
    """Состояния диалога для команды /track."""

    WAITING_FOR_URL = auto()
    WAITING_FOR_TAGS = auto()


async def track_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога /track."""
    user, message, _ = get_update_fields(update)

    await message.reply_text(
        "**Добавление новой ссылки для отслеживания**\n\n"
        "Отправьте мне ссылку, которую хотите отслеживать.\n\n"
        "Поддерживаются:\n"
        "• **GitHub** репозитории (https://github.com/owner/repo)\n"
        "• **StackOverflow** вопросы (https://stackoverflow.com/questions/12345)\n\n"
        "Или отправьте /cancel для отмены."
    )

    logger.info("track_dialog_started", user_id=user.id)
    return TrackState.WAITING_FOR_URL.value


async def track_receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение ссылки от пользователя."""
    message = update.message
    if message is None:
        return ConversationHandler.END
    text = message.text
    if text is None:
        return ConversationHandler.END
    url = text.strip()

    # Проверка на отмену
    if url == "/cancel":
        await message.reply_text("❌ Отслеживание отменено.")
        return ConversationHandler.END

    # Простая валидация ссылки
    if not is_supported_url(url):
        await message.reply_text(
            "❌ **Неподдерживаемая ссылка**\n\n"
            "Поддерживаются только:\n"
            "• GitHub репозитории\n"
            "• StackOverflow вопросы\n\n"
            "Попробуйте снова или отправьте /cancel"
        )
        return TrackState.WAITING_FOR_URL.value

    # Сохраняем URL в context.user_data
    user_data = get_user_data(context)
    user_data["tracking_url"] = url

    await message.reply_text(
        "✅ **Ссылка принята!**\n\n"
        "Теперь отправьте **теги** через запятую (необязательно).\n"
        "Теги помогут вам классифицировать ссылки.\n\n"
        "Пример: `работа, баг, документация`\n\n"
        "Или отправьте:\n"
        "• `/skip` чтобы пропустить\n"
        "• `/cancel` для отмены"
    )

    return TrackState.WAITING_FOR_TAGS.value


async def track_receive_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение тегов от пользователя."""
    user, message, text = get_update_fields(update)

    text = text.strip()

    user_data = get_user_data(context)
    if text == "/cancel":
        user_data.pop("tracking_url", None)
        await message.reply_text("❌ Отслеживание отменено.")
        return ConversationHandler.END

    # Парсим теги
    tags = []
    if text != "/skip":
        tags = [tag.strip() for tag in text.split(",") if tag.strip()]

    # Получаем URL из context
    url = user_data.get("tracking_url")

    if not url:
        await message.reply_text(
            "❌ Ошибка: ссылка не найдена. Начните заново с /track"
        )
        return ConversationHandler.END

    # Отправляем запрос в Scrapper
    result = await scrapper_client.add_link(user.id, url, tags)

    # Очищаем временные данные
    user_data.pop("tracking_url", None)

    if result is None:
        # Scrapper вернул 409 Conflict
        await message.reply_text(
            "⚠️ **Ссылка уже отслеживается!**\n\n"
            "Используйте /list чтобы посмотреть все ваши ссылки."
        )
        logger.info("link_already_tracked", user_id=user.id, url=url)
    else:
        # Успешно добавлено
        tags_text = f" с тегами: **{', '.join(tags)}**" if tags else " без тегов"
        await message.reply_text(
            f"✅ **Ссылка добавлена!**{tags_text}\n\n"
            f"URL: {url}\n\n"
            f"Я начну отслеживать изменения и уведомлю вас."
        )
        logger.info("link_added", user_id=user.id, url=url, tags=tags)

    return ConversationHandler.END


async def track_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога."""
    user, message, _ = get_update_fields(update)
    user_data = get_user_data(context)
    user_data.pop("tracking_url", None)
    await message.reply_text("❌ Отслеживание отменено.")
    logger.info("track_dialog_cancelled", user_id=user.id)
    return ConversationHandler.END


def is_supported_url(url: str) -> bool:
    """Проверяет, поддерживается ли ссылка."""
    return url.startswith(
        ("https://github.com/", "https://stackoverflow.com/questions/")
    )
