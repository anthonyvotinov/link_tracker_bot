from jinja2 import Environment, FileSystemLoader
from telegram import Update
from telegram.ext import ContextTypes

from src.bot_service.clients.scrapper_client import scrapper_client
from src.bot_service.logger import logger
from src.bot_service.tools import get_update_fields

environment = Environment(loader=FileSystemLoader("src/data/messages/"))
welcome_template = environment.get_template("welcome_message.txt")
help_template = environment.get_template("help_message.txt")
error_template = environment.get_template("error_message.txt")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user, message, _ = get_update_fields(update)
    user_id = user.id

    # Регистрируем чат в Scrapper
    await scrapper_client.register_chat(user_id)

    logger.info(
        "user_started",
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
    )

    welcome_message = welcome_template.render(first_name=user.first_name)
    await message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    user, message, _ = get_update_fields(update)
    user_id = user.id

    logger.info("help_command_called", user_id=user_id)

    help_text = help_template.render()
    await message.reply_text(help_text)


async def handle_unknown_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обрабатывает все неизвестные команды."""
    user, message, _ = get_update_fields(update)
    user_id = user.id
    command = message.text if update.message else "unknown"

    logger.warning("unknown_command_received", user_id=user_id, command=command)

    error_message = error_template.render()
    await message.reply_text(error_message)
