"""Chat API router — SSE streaming."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.ai.agent import run_agent, run_agent_stream
from backend.ai import provider

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


@router.post("")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Non-streaming chat endpoint."""
    if not provider.is_configured():
        return {"error": "AI provider not configured. Go to Settings to configure.", "response": None}

    response = await run_agent(req.message, db, conversation_history=req.history)
    return {"response": response}


@router.post("/stream")
async def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """SSE streaming chat endpoint."""
    if not provider.is_configured():
        return {"error": "AI provider not configured"}

    async def event_generator():
        async for chunk in run_agent_stream(req.message, db, conversation_history=req.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
