import asyncio
from backend.db.database import get_engine, SessionLocal
from backend.routers.chat import chat_briefing, ChatBriefingRequest

async def run():
    db = SessionLocal()
    req = ChatBriefingRequest(period="weekly")
    res = await chat_briefing(req, db)
    print(res)

asyncio.run(run())
