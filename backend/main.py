from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.db.database import init_db
from backend.db.seed import seed_default_categories
from backend.routers import auth, transactions, holdings, import_data, dashboard, chat, briefings, settings as settings_router


app = FastAPI(
    title="ClawFin",
    description="Your AI grip on Canadian finances",
    version="0.1.0",
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(holdings.router, prefix="/api/holdings", tags=["holdings"])
app.include_router(import_data.router, prefix="/api/import", tags=["import"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(briefings.router, prefix="/api/briefings", tags=["briefings"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])


@app.on_event("startup")
def on_startup():
    init_db()
    seed_default_categories()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
