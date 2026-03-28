"""Settings API router — AI config, categories, contribution room."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.db.models import Category, AppConfig, DEFAULT_CATEGORIES

router = APIRouter()


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
    from backend.config import settings
    return {
        "provider": settings.AI_PROVIDER,
        "model": settings.AI_MODEL,
        "base_url": settings.AI_BASE_URL,
        "has_api_key": bool(settings.AI_API_KEY),
        "is_configured": bool(settings.AI_PROVIDER and settings.AI_MODEL),
    }


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
