from fastapi.testclient import TestClient
from backend.main import app
from backend.db.database import SessionLocal, Base, get_engine
from backend.config import settings

# Override auth to bypass it for this script
from backend.routers import auth
app.dependency_overrides[auth.require_auth] = lambda: None

client = TestClient(app)

res = client.post("/api/chat/briefing", json={"period": "weekly"})
print("STATUS:", res.status_code)
print("BODY:", res.text)
