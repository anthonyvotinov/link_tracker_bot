from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from src.ai_agent_service.services.handler import Handler
from src.ai_agent_service.logger import logger

handler = Handler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом AI Agent Service."""
    logger.info("ai_agent_starting")
    await handler.start()
    yield
    logger.info("ai_agent_shutting_down")
    await handler.stop()


app = FastAPI(
    title="AI Agent Service",
    description="Фильтрация и суммаризация обновлений",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-agent"}


def main():
    uvicorn.run(
        "src.ai_agent_service.main:app", host="0.0.0.0", port=8001, log_level="info"
    )


if __name__ == "__main__":
    main()
