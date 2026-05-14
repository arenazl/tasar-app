"""Endpoints AI: chat conversacional con Tasador AI + análisis."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from core.security import get_current_user
from models.user import User
from services.ai_router import chat_stream, chat_complete, SYSTEM_TASADOR


router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    system: Optional[str] = None


@router.post("/chat/stream")
async def stream_chat(body: ChatRequest, user: User = Depends(get_current_user)):
    """SSE streaming del Tasador AI."""

    async def event_gen():
        async for chunk in chat_stream(
            prompt=body.message,
            system=body.system or SYSTEM_TASADOR,
            session_id=body.session_id,
        ):
            # SSE: cada evento como `data: ...`
            data = chunk.replace("\n", "\\n")
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/chat")
async def complete_chat(body: ChatRequest, user: User = Depends(get_current_user)):
    """Versión sync (no streaming)."""
    out = await chat_complete(body.message, system=body.system or SYSTEM_TASADOR)
    return {"response": out}
