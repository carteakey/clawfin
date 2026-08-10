from sqlalchemy.orm import Session
from backend.db.database import SessionLocal
from backend.db.models import Category, DEFAULT_CATEGORIES


def seed_default_categories():
    """Seed default categories. Idempotently adds any new defaults on upgrade."""
    db: Session = SessionLocal()
    try:
        existing_names = {c.name for c in db.query(Category).all()}
        current_max_order = db.query(Category).count()

        added = 0
        for i, cat in enumerate(DEFAULT_CATEGORIES):
            if cat["name"] in existing_names:
                continue
            db.add(Category(
                name=cat["name"],
                icon=cat["icon"],
                color=cat["color"],
                is_default=True,
                sort_order=current_max_order + added,
            ))
            added += 1

        if added:
            db.commit()
    finally:
        db.close()
