from fastapi import APIRouter, Request, HTTPException, status
from src.bot_service.api.models import LinkUpdate, ApiErrorResponse
from src.bot_service.services.http_update_handler import update_handler
from src.bot_service.logger import logger
from src.bot_service.main import limiter
from src.bot_service.config import settings

router: APIRouter = APIRouter(prefix="/api")


@router.post("/updates", status_code=status.HTTP_200_OK)
@limiter.limit(
    f"{settings.RATE_LIMIT_MAX_REQUESTS}/{settings.RATE_LIMIT_WINDOW_SECONDS}second"
)
async def receive_update(request: Request, update: LinkUpdate):
    """
    Получить обновление от Scrapper сервиса.
    """
    logger.info(
        "update_received",
        link_id=update.id,
        url=str(update.url),
        chat_ids=update.tgChatIds,
    )

    try:
        await update_handler.process_update(update)
        return {"status": "ok", "message": "Update processed"}
    except ValueError as e:
        error_response = ApiErrorResponse(
            description="Invalid update data",
            code="400",
            exceptionName="ValueError",
            exceptionMessage=str(e),
            stacktrace=None,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_response.model_dump()
        )
    except Exception as e:
        logger.error("update_processing_error", error=str(e))
        error_response = ApiErrorResponse(
            description="Internal server error",
            code="500",
            exceptionName=e.__class__.__name__,
            exceptionMessage=str(e),
            stacktrace=None,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(),
        )
