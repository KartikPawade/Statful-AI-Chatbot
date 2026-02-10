from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import Redis

from app.api.routes import router
from app.core.config import get_settings
from app.db.redis_store import ChatRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create Redis connection and repository at startup; close on shutdown."""
    settings = get_settings()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
    app.state.redis = redis_client
    app.state.chat_repository = ChatRepository(redis_client)
    yield
    redis_client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Stateful AI Chatbot", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()

