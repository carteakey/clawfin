from sqlalchemy.orm import Session
from backend.db.database import SessionLocal
from backend.db.models import Category, DEFAULT_CATEGORIES


def seed_default_categories():
    """Seed default categories if the table is empty."""
    db: Session = SessionLocal()
    try:
        existing = db.query(Category).count()
        if existing == 0:
            for i, cat in enumerate(DEFAULT_CATEGORIES):
                db.add(Category(
                    name=cat["name"],
                    icon=cat["icon"],
                    color=cat["color"],
                    is_default=True,
                    sort_order=i,
                ))
            db.commit()
    finally:
        db.close()
