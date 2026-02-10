from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.services.chat_service import ChatService


router = APIRouter()


def get_chat_service(request: Request) -> ChatService:
    return ChatService(
        settings=get_settings(),
        repository=request.app.state.chat_repository,
    )


@router.get("/")
def home():
    return {"status": "AI Server is running"}


@router.get("/ask")
async def ask_ai(
    prompt: str,
    provider: str = "gemini",
    session_id: str | None = None,
    memory: str = "rolling",
    service: ChatService = Depends(get_chat_service),
) -> dict:
    """
    Unified endpoint to switch between cloud and local models.

    Query params:
    - provider: 'gemini' or 'ollama'
    - session_id: optional session key for context/memory
    - memory: 'rolling' | 'window' | 'none'
    """
    try:
        result = service.ask(
            prompt=prompt,
            provider=provider,
            session_id=session_id,
            memory=memory,
        )
        return {"provider": result.provider, "reply": result.reply, "session_id": result.session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(service: ChatService = Depends(get_chat_service)) -> dict:
    """List available Gemini models."""
    try:
        return {"models": service.list_gemini_models()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

