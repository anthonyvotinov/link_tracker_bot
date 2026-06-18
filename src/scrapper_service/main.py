from contextlib import asynccontextmanager

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from api.models import ApiErrorResponse
from src.scrapper_service.config import settings, AccessType
from src.scrapper_service.database import db_factory
from src.scrapper_service.api.routes import router
from src.scrapper_service.repos.base import (
    LinkRepository,
    ChatRepository,
    SubscriptionRepository,
)

from src.scrapper_service.services.message_sender import MessageSender
from src.scrapper_service.services.update_sender import UpdateSender
from src.scrapper_service.services.kafka_sender import KafkaMessageSender
from src.scrapper_service.services.tracker_service import TrackerService
from src.scrapper_service.scheduler import Scheduler

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        f"{settings.RATE_LIMIT_MAX_REQUESTS}/{settings.RATE_LIMIT_WINDOW_SECONDS}second"
    ],
)


async def rate_limit_exceeded_handler(request: Request, exc: Exception):
    if not isinstance(exc, RateLimitExceeded):
        raise exc
    return JSONResponse(
        status_code=429,
        content=ApiErrorResponse(
            description="Rate limit exceeded. Too many requests from this IP.",
            code="429",
            exceptionName="RateLimitExceeded",
            exceptionMessage=exc.detail,
        ).model_dump(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_factory.init()
    from src.database.migrations import run_migrations

    await run_migrations()

    if settings.ACCESS_TYPE == AccessType.SQL:
        from src.repos.sql.chat_repository import SqlChatRepository
        from src.repos.sql.link_repository import SqlLinkRepository
        from src.repos.sql.subscription_repository import SqlSubscriptionRepository

        pool = db_factory.get_pool()
        chat_repo: ChatRepository = SqlChatRepository(pool)
        link_repo: LinkRepository = SqlLinkRepository(pool)
        sub_repo: SubscriptionRepository = SqlSubscriptionRepository(pool)
    else:
        from src.repos.orm.orm_chat_repository import OrmChatRepository
        from src.repos.orm.orm_link_repository import OrmLinkRepository
        from src.repos.orm.orm_subscription_repository import OrmSubscriptionRepository

        session = db_factory.get_session()
        chat_repo = OrmChatRepository(session)
        link_repo = OrmLinkRepository(session)
        sub_repo = OrmSubscriptionRepository(session)

    app.state.chat_repo = chat_repo
    app.state.link_repo = link_repo
    app.state.sub_repo = sub_repo
    app.state.limiter = limiter

    sender: MessageSender

    if settings.NOTIFICATION_BACKEND == "kafka":
        sender = KafkaMessageSender()
    else:
        sender = UpdateSender()
    await sender.start()

    tracker_service = TrackerService(link_repo, sub_repo, sender)
    app.state.tracker_service = tracker_service

    scheduler = Scheduler(tracker_service)
    app.state.scheduler = scheduler
    scheduler.start()

    yield

    scheduler.shutdown()
    await sender.close()
    await db_factory.close()


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)


app.include_router(router)


def main():
    uvicorn.run(
        "src.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True
    )


if __name__ == "__main__":
    main()
