#!/usr/bin/env python3
"""
Точка входа для Telegram бота LinkTracker.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from telegram import BotCommand
from src.bot_service.config import settings
from src.bot_service.logger import logger
from src.bot_service.handlers.commands import (
    start,
    help_command,
    handle_unknown_command,
)
from src.bot_service.handlers.track import (
    track_start,
    track_receive_url,
    track_receive_tags,
    track_cancel,
    TrackState,
)
from src.bot_service.handlers.links import untrack, list_links, handle_untrack_choice
from src.bot_service.api.routes import router as api_router
from src.bot_service.services.http_update_handler import update_handler
from src.bot_service.services.kafka_consumer import KafkaUpdateConsumer

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        f"{settings.RATE_LIMIT_MAX_REQUESTS}/{settings.RATE_LIMIT_WINDOW_SECONDS}second"
    ],
)

fastapi_app = FastAPI(
    title="Bot API",
    description="API для получения обновлений от Scrapper сервиса",
    version="1.0.0",
    contact={"name": "Alexander Biryukov", "url": "https://github.com"},
)

fastapi_app.add_middleware(SlowAPIMiddleware)


@fastapi_app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={
            "description": "Rate limit exceeded. Too many requests from this IP.",
            "code": "429",
            "exceptionName": "RateLimitExceeded",
        },
    )


fastapi_app.include_router(api_router)

telegram_app = None
kafka_consumer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app, kafka_consumer
    logger.info("bot_api_starting", host=settings.API_HOST, port=settings.API_PORT)

    try:
        telegram_app = (
            Application.builder()
            .token(settings.BOT_TOKEN)
            .base_url(f"{settings.PROXY}/bot")
            .build()
        )

        await register_handlers(telegram_app)
        await telegram_app.initialize()
        await telegram_app.start()
        if telegram_app.updater is not None:
            await telegram_app.updater.start_polling()

        update_handler.init_bot(telegram_app.bot)
        logger.info("telegram_bot_started")

        if settings.MESSAGE_SOURCE == "kafka":
            kafka_consumer = KafkaUpdateConsumer(bot=telegram_app.bot)
            await kafka_consumer.start()

        yield

    finally:
        logger.info("bot_api_shutting_down")
        if kafka_consumer:
            await kafka_consumer.stop()
        if telegram_app:
            if telegram_app.updater is not None:
                await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()


fastapi_app.router.lifespan_context = lifespan


async def register_handlers(app: Application):
    commands = [
        BotCommand("start", "Запустить бота и получить приветствие"),
        BotCommand("help", "Показать список всех команд"),
        BotCommand("track", "Начать отслеживание ссылки"),
        BotCommand("untrack", "Прекратить отслеживание ссылки"),
        BotCommand("list", "Показать список отслеживаемых ссылок"),
    ]
    await app.bot.set_my_commands(commands)
    track_handler = ConversationHandler(
        entry_points=[CommandHandler("track", track_start)],
        states={
            TrackState.WAITING_FOR_URL.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, track_receive_url),
                CommandHandler("cancel", track_cancel),
            ],
            TrackState.WAITING_FOR_TAGS.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, track_receive_tags),
                CommandHandler("skip", track_receive_tags),
                CommandHandler("cancel", track_cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", track_cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(track_handler)
    app.add_handler(CommandHandler("untrack", untrack))
    app.add_handler(CommandHandler("list", list_links))
    app.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_untrack_choice,
        )
    )
    logger.info("handlers_registered")


def main():
    uvicorn.run(
        fastapi_app, host=settings.API_HOST, port=settings.API_PORT, log_level="info"
    )


if __name__ == "__main__":
    main()
