from fastapi import APIRouter, Request, Header, HTTPException, status
import re
from pydantic import HttpUrl
from src.scrapper_service.api.models import (
    LinkResponse,
    ApiErrorResponse,
    AddLinkRequest,
    RemoveLinkRequest,
    ListLinksResponse,
)
from src.scrapper_service.logger import logger

router = APIRouter()


def detect_resource_type(url: str) -> tuple[str, str]:
    """Определяет тип ресурса и его ID."""
    if "github.com" in url:
        match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
        if match:
            return "github", f"{match.group(1)}/{match.group(2)}"
    elif "stackoverflow.com/questions/" in url:
        match = re.search(r"/questions/(\d+)", url)
        if match:
            return "stackoverflow", match.group(1)
    raise ValueError(f"Unsupported URL type: {url}")


@router.post("/tg-chat/{id}", status_code=status.HTTP_200_OK)
async def register_chat(id: int, request: Request):
    chat_repo = request.app.state.chat_repo
    logger.info("register_chat_request", chat_id=id)

    if await chat_repo.exists(id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ApiErrorResponse(
                description="Chat already exists",
                code="409",
                exceptionName="ChatAlreadyExistsError",
                exceptionMessage=f"Chat with id {id} already registered",
            ).model_dump(),
        )

    await chat_repo.add(id)
    return {"message": "Chat registered successfully"}


@router.delete("/tg-chat/{id}", status_code=status.HTTP_200_OK)
async def delete_chat(id: int, request: Request):
    chat_repo = request.app.state.chat_repo
    logger.info("delete_chat_request", chat_id=id)

    if not await chat_repo.exists(id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Chat not found",
                code="404",
                exceptionName="ChatNotFoundError",
                exceptionMessage=f"Chat with id {id} does not exist",
            ).model_dump(),
        )

    await chat_repo.delete(id)
    return {"message": "Chat deleted successfully"}


@router.get("/links", response_model=ListLinksResponse)
async def get_links(
    request: Request, tg_chat_id: int = Header(..., alias="Tg-Chat-Id")
):
    chat_repo = request.app.state.chat_repo
    sub_repo = request.app.state.sub_repo
    logger.info("get_links_request", chat_id=tg_chat_id)

    if not await chat_repo.exists(tg_chat_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Chat not found",
                code="404",
                exceptionName="ChatNotFoundError",
            ).model_dump(),
        )

    raw_links = await sub_repo.get_chat_links(tg_chat_id)

    link_responses = [
        LinkResponse(
            id=item["id"],
            url=HttpUrl(item["url"]),
            tags=item.get("tags", []),
            filters=[],
        )
        for item in raw_links
    ]
    return ListLinksResponse(links=link_responses, size=len(link_responses))


@router.post("/links", response_model=LinkResponse)
async def add_link(
    request: Request,
    payload: AddLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
):
    chat_repo = request.app.state.chat_repo
    link_repo = request.app.state.link_repo
    sub_repo = request.app.state.sub_repo
    logger.info("add_link_request", chat_id=tg_chat_id, url=str(payload.link))

    if not await chat_repo.exists(tg_chat_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Chat not found",
                code="404",
                exceptionName="ChatNotFoundError",
            ).model_dump(),
        )

    url_str = str(payload.link)
    try:
        resource_type, resource_id = detect_resource_type(url_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ApiErrorResponse(
                description=str(e),
                code="400",
                exceptionName="InvalidUrlError",
            ).model_dump(),
        )

    link_id = await link_repo.get_or_create(url_str, resource_type, resource_id)

    await sub_repo.add(tg_chat_id, link_id, payload.tags)

    return LinkResponse(
        id=link_id,
        url=HttpUrl(url_str),
        tags=payload.tags,
        filters=payload.filters,
    )


@router.delete("/links", response_model=LinkResponse)
async def remove_link(
    request: Request,
    payload: RemoveLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
):
    chat_repo = request.app.state.chat_repo
    sub_repo = request.app.state.sub_repo
    logger.info("remove_link_request", chat_id=tg_chat_id, url=str(payload.link))

    if not await chat_repo.exists(tg_chat_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Chat not found",
                code="404",
                exceptionName="ChatNotFoundError",
            ).model_dump(),
        )

    url_str = str(payload.link)

    chat_links = await sub_repo.get_chat_links(tg_chat_id)
    link_data = next((link for link in chat_links if link["url"] == url_str), None)

    if not link_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Link not found",
                code="404",
                exceptionName="LinkNotFoundError",
                exceptionMessage=f"Link {url_str} not found for chat {tg_chat_id}",
            ).model_dump(),
        )

    await sub_repo.remove(tg_chat_id, link_data["id"])

    return LinkResponse(
        id=link_data["id"],
        url=HttpUrl(url_str),
        tags=link_data.get("tags", []),
        filters=[],
    )
