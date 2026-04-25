"""Chat API router — SSE streaming."""
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.ai.agent import run_agent, run_agent_stream
from backend.ai.briefings import build_transaction_briefing_context, generate_transaction_briefing
from backend.ai import provider

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


class ChatBriefingRequest(BaseModel):
    period: str
    include_transactions: bool = False
    max_transactions: int = 25
    redact_merchants: bool = False


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


@router.post("/briefing")
async def chat_briefing(req: ChatBriefingRequest, db: Session = Depends(get_db)):
    """Generate a UI-safe briefing through normal app auth."""
    if req.period not in ("daily", "weekly"):
        return {"error": "period must be 'daily' or 'weekly'", "summary": None}
    if not provider.is_configured():
        return {"error": "AI provider not configured. Go to Settings to configure.", "summary": None}

    context = build_transaction_briefing_context(
        db,
        period=req.period,
        include_transactions=req.include_transactions,
        max_transactions=req.max_transactions,
        redact_merchants=req.redact_merchants,
    )

    try:
        summary = await generate_transaction_briefing(context)
    except httpx.HTTPError as exc:
        return {"error": f"AI provider request failed: {str(exc)[:200]}", "summary": None, "context": context}
    except RuntimeError as exc:
        return {"error": str(exc), "summary": None, "context": context}

    return {"summary": summary, "context": context}
