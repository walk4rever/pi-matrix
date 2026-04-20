"""
Thin HTTP wrapper around hermes AIAgent.
Receives messages from cloud router, runs hermes, posts reply back.
"""
import asyncio
import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from run_agent import AIAgent

app = FastAPI()

ROUTER_REPLY_URL = os.environ["ROUTER_REPLY_URL"]
HERMES_MODEL = os.environ.get("HERMES_MODEL", "anthropic/claude-haiku-4-5")

# One agent per container = one user, conversation context preserved across messages
agent = AIAgent(model=HERMES_MODEL)


class InboxMessage(BaseModel):
    open_id: str
    text: str


@app.post("/inbox")
async def inbox(msg: InboxMessage):
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, agent.run_conversation, msg.text)
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(ROUTER_REPLY_URL, json={"open_id": msg.open_id, "text": response})
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
