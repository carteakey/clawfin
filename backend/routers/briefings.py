"""Briefing API router for scheduled external automation."""
import hmac
from datetime import date

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.ai.briefings import build_transaction_briefing_context, generate_transaction_briefing
from backend.config import settings
from backend.db.database import get_db

router = APIRouter()


class TransactionBriefingRequest(BaseModel):
    period: str = Field("daily", pattern="^(daily|weekly)$")
    mode: str = Field("generate", pattern="^(context|generate)$")
    end_date: date | None = None
    include_transactions: bool = False
    max_transactions: int = Field(25, ge=0, le=100)
    redact_merchants: bool = False


def require_automation_token(
    x_clawfin_automation_token: str | None = Header(default=None),
):
    if not settings.AUTOMATION_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Automation token not configured. Set CLAWFIN_AUTOMATION_TOKEN.",
        )
    if not x_clawfin_automation_token:
        raise HTTPException(status_code=401, detail="Missing automation token")
    if not hmac.compare_digest(x_clawfin_automation_token, settings.AUTOMATION_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid automation token")


@router.post("/transactions", dependencies=[Depends(require_automation_token)])
async def transaction_briefing(
    req: TransactionBriefingRequest,
    db: Session = Depends(get_db),
):
    context = build_transaction_briefing_context(
        db,
        period=req.period,
        end_date=req.end_date,
        include_transactions=req.include_transactions,
        max_transactions=req.max_transactions,
        redact_merchants=req.redact_merchants,
    )

    result = {
        "period": req.period,
        "mode": req.mode,
        "range": context["range"],
        "context": context,
    }

    if req.mode == "context":
        return result

    try:
        result["summary"] = await generate_transaction_briefing(context)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI provider request failed: {str(exc)[:200]}")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result
