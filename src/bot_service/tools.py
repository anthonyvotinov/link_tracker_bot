from typing import Any, Tuple

from telegram import User, Message
from telegram.ext import ContextTypes


def get_update_fields(update: Any) -> Tuple[User, Message, str]:
    return update.effective_user, update.message, update.message.text


def get_user_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if context.user_data:
        return context.user_data
    return {}
