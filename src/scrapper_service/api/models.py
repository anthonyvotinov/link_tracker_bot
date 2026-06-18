from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional


class LinkResponse(BaseModel):
    """Ответ с информацией о ссылке."""

    id: int = Field(..., description="ID ссылки")
    url: HttpUrl = Field(..., description="URL отслеживаемой ссылки")
    tags: List[str] = Field(default=[], description="Теги ссылки")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "url": "https://github.com/owner/repo",
                "tags": ["work", "opensource"],
                "filters": ["bugs"],
            }
        }


class ApiErrorResponse(BaseModel):
    """Ответ с ошибкой API."""

    description: str = Field(..., description="Описание ошибки")
    code: str = Field(..., description="Код ошибки")
    exceptionName: Optional[str] = Field(None, description="Имя исключения")
    exceptionMessage: Optional[str] = Field(None, description="Сообщение исключения")
    stacktrace: Optional[List[str]] = Field(None, description="Стек вызовов")

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Чат уже существует",
                "code": "409",
                "exceptionName": "ChatAlreadyExistsException",
                "exceptionMessage": "Chat with id 123 already registered",
            }
        }


class AddLinkRequest(BaseModel):
    """Запрос на добавление ссылки."""

    link: HttpUrl = Field(..., description="URL для отслеживания")
    tags: List[str] = Field(default=[], description="Теги ссылки")
    filters: List[str] = Field(default=[], description="Фильтры для ссылки")

    class Config:
        json_schema_extra = {
            "example": {
                "link": "https://github.com/owner/repo",
                "tags": ["work", "important"],
                "filters": ["releases"],
            }
        }


class RemoveLinkRequest(BaseModel):
    """Запрос на удаление ссылки."""

    link: HttpUrl = Field(..., description="URL для удаления из отслеживания")

    class Config:
        json_schema_extra = {"example": {"link": "https://github.com/owner/repo"}}


class ListLinksResponse(BaseModel):
    """Ответ со списком ссылок."""

    links: List[LinkResponse] = Field(..., description="Список отслеживаемых ссылок")
    size: int = Field(..., description="Количество ссылок")

    class Config:
        json_schema_extra = {
            "example": {
                "links": [
                    {
                        "id": 1,
                        "url": "https://github.com/owner/repo1",
                        "tags": ["work"],
                        "filters": [],
                    },
                    {
                        "id": 2,
                        "url": "https://stackoverflow.com/questions/12345",
                        "tags": ["help"],
                        "filters": [],
                    },
                ],
                "size": 2,
            }
        }
