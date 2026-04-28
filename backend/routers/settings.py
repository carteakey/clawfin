"""Settings API router — AI config, categories, rules, contribution room."""
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.config import settings as app_settings
from backend.db.database import get_db
from backend.db.models import Category, CategoryRule, AppConfig, DEFAULT_CATEGORIES
from backend.security import encrypt_value

router = APIRouter()


@router.get("/export")
def export_database():
    """Download the SQLite DB file as a backup."""
    db_path = Path(app_settings.DB_PATH)
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    filename = f"clawfin-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    return FileResponse(
        path=str(db_path),
        filename=filename,
        media_type="application/octet-stream",
    )


def _get_flag(db: Session, key: str, default: bool = False) -> bool:
    row = db.query(AppConfig).filter(AppConfig.key == key).first()
    if not row:
        return default
    return row.value.strip().lower() in ("1", "true", "yes", "on")


def _set_flag(db: Session, key: str, value: bool):
    row = db.query(AppConfig).filter(AppConfig.key == key).first()
    if row:
        row.value = "true" if value else "false"
    else:
        db.add(AppConfig(key=key, value="true" if value else "false"))


# ─── Categories ──────────────────────────────────────────────────────

@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).order_by(Category.sort_order).all()
    return {
        "categories": [
            {"id": c.id, "name": c.name, "icon": c.icon, "color": c.color, "is_default": c.is_default}
            for c in cats
        ]
    }


class CategoryCreate(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None


@router.post("/categories")
def create_category(req: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == req.name).first()
    if existing:
        return {"error": f"Category '{req.name}' already exists"}

    max_order = db.query(Category).count()
    cat = Category(name=req.name, icon=req.icon, color=req.color, is_default=False, sort_order=max_order)
    db.add(cat)
    db.commit()
    return {"id": cat.id, "name": cat.name}


@router.delete("/categories/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        return {"error": "Category not found"}
    db.delete(cat)
    db.commit()
    return {"status": "deleted"}


@router.post("/categories/reset")
def reset_categories(db: Session = Depends(get_db)):
    """Reset to default 12 categories."""
    db.query(Category).delete()
    for i, cat in enumerate(DEFAULT_CATEGORIES):
        db.add(Category(name=cat["name"], icon=cat["icon"], color=cat["color"], is_default=True, sort_order=i))
    db.commit()
    return {"status": "reset", "count": len(DEFAULT_CATEGORIES)}


# ─── AI Config ───────────────────────────────────────────────────────

@router.get("/ai")
def get_ai_config(db: Session = Depends(get_db)):
    from backend.ai.provider import _get_provider_config
    cfg = _get_provider_config()
    return {
        "provider": cfg["provider"],
        "model": cfg["model"],
        "base_url": cfg["base_url"],
        "has_api_key": bool(cfg["api_key"]),
        "is_configured": bool(cfg["provider"] and cfg["model"]),
    }


class AIFlagsUpdate(BaseModel):
    ai_categorization_enabled: bool | None = None
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    clear_api_key: bool | None = None


def _set_override(db: Session, key: str, value: str | None):
    row = db.query(AppConfig).filter(AppConfig.key == key).first()
    if value is None or value == "":
        if row:
            db.delete(row)
        return
    if key in {"ai_api_key_override", "simplefin_access_url"}:
        value = encrypt_value(value)
    if row:
        row.value = value
    else:
        db.add(AppConfig(key=key, value=value))


@router.get("/ai/flags")
def get_ai_flags(db: Session = Depends(get_db)):
    from backend.ai.provider import _get_provider_config
    cfg = _get_provider_config(db)
    return {
        "ai_categorization_enabled": _get_flag(db, "ai_categorization_enabled", False),
        "provider": cfg["provider"],
        "base_url": cfg["base_url"],
        "model": cfg["model"],
        "has_api_key": bool(cfg["api_key"]),
    }


@router.put("/ai/flags")
def update_ai_flags(req: AIFlagsUpdate, db: Session = Depends(get_db)):
    if req.ai_categorization_enabled is not None:
        _set_flag(db, "ai_categorization_enabled", req.ai_categorization_enabled)
    if req.provider is not None:
        _set_override(db, "ai_provider_override", req.provider.lower() or None)
        # Clear model override when provider changes (model may not exist in new provider)
        _set_override(db, "ai_model_override", None)
    if req.base_url is not None:
        _set_override(db, "ai_base_url_override", req.base_url)
    if req.model is not None:
        _set_override(db, "ai_model_override", req.model)
    if req.clear_api_key:
        _set_override(db, "ai_api_key_override", None)
    elif req.api_key is not None:
        _set_override(db, "ai_api_key_override", req.api_key)
    db.commit()
    return {"status": "updated"}


@router.get("/ai/health")
async def get_ai_health():
    """Reachability check for the configured AI provider."""
    from backend.ai.provider import _get_provider_config

    config = _get_provider_config()
    provider_fmt = config["format"]
    base_url = config["base_url"]

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            if provider_fmt == "ollama":
                r = await client.get(f"{base_url}/api/tags")
                r.raise_for_status()
                models = [m.get("name") for m in r.json().get("models", [])]
                return {"ok": True, "provider": "ollama", "models": models}
            if provider_fmt == "anthropic":
                # No cheap health check; just validate credentials present
                if not config["api_key"]:
                    return {"ok": False, "error": "No API key"}
                return {"ok": True, "provider": "anthropic", "note": "no-op check"}
            # openai-compatible: list models
            headers = {}
            if config["api_key"]:
                headers["Authorization"] = f"Bearer {config['api_key']}"
            r = await client.get(f"{base_url}/v1/models", headers=headers)
            r.raise_for_status()
            data = r.json()
            models = [m.get("id") for m in data.get("data", [])][:20]
            return {"ok": True, "provider": "openai", "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# ─── Categorization rules ────────────────────────────────────────────


class RuleCreate(BaseModel):
    pattern: str
    category: str
    priority: int = 1
    is_regex: bool = False


@router.post("/rules")
def create_rule(req: RuleCreate, db: Session = Depends(get_db)):
    pattern = req.pattern.strip().lower()
    if not pattern:
        return {"error": "Pattern required"}
    existing = db.query(CategoryRule).filter(CategoryRule.pattern == pattern).first()
    if existing:
        existing.category = req.category
        existing.priority = max(existing.priority, req.priority)
        db.commit()
        return {"status": "updated", "id": existing.id}
    rule = CategoryRule(
        pattern=pattern,
        category=req.category,
        priority=req.priority,
        is_regex=req.is_regex,
    )
    db.add(rule)
    db.commit()
    return {"status": "created", "id": rule.id}


@router.get("/rules")
def list_rules(db: Session = Depends(get_db)):
    rules = (
        db.query(CategoryRule)
        .order_by(CategoryRule.priority.desc(), CategoryRule.id.asc())
        .all()
    )
    return {
        "rules": [
            {
                "id": r.id,
                "pattern": r.pattern,
                "category": r.category,
                "priority": r.priority,
                "is_regex": r.is_regex,
            }
            for r in rules
        ]
    }


class RuleUpdate(BaseModel):
    category: str | None = None


@router.patch("/rules/{rule_id}")
def update_rule(rule_id: int, req: RuleUpdate, db: Session = Depends(get_db)):
    r = db.query(CategoryRule).filter(CategoryRule.id == rule_id).first()
    if not r:
        return {"error": "Rule not found"}
    if req.category is not None:
        r.category = req.category
    db.commit()
    return {"status": "updated", "id": rule_id}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    r = db.query(CategoryRule).filter(CategoryRule.id == rule_id).first()
    if not r:
        return {"error": "Rule not found"}
    db.delete(r)
    db.commit()
    return {"status": "deleted"}


# ─── Contribution Room ──────────────────────────────────────────────

@router.get("/contribution-room")
def get_contribution_room(db: Session = Depends(get_db)):
    room = {}
    for key in ["tfsa_room", "rrsp_room", "fhsa_room"]:
        config = db.query(AppConfig).filter(AppConfig.key == key).first()
        room[key] = float(config.value) if config else None
    return room


class ContributionRoomUpdate(BaseModel):
    tfsa_room: float | None = None
    rrsp_room: float | None = None
    fhsa_room: float | None = None


@router.put("/contribution-room")
def update_contribution_room(req: ContributionRoomUpdate, db: Session = Depends(get_db)):
    for key, value in [("tfsa_room", req.tfsa_room), ("rrsp_room", req.rrsp_room), ("fhsa_room", req.fhsa_room)]:
        if value is not None:
            config = db.query(AppConfig).filter(AppConfig.key == key).first()
            if config:
                config.value = str(value)
            else:
                db.add(AppConfig(key=key, value=str(value)))
    db.commit()
    return {"status": "updated"}
