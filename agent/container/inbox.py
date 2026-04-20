"""
Thin HTTP wrapper around hermes AIAgent.
Calls our LiteLLM Gateway — no direct LLM API keys needed in this container.
"""
import asyncio
import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from run_agent import AIAgent

app = FastAPI()

ROUTER_REPLY_URL = os.environ["ROUTER_REPLY_URL"]
GATEWAY_URL      = os.environ["GATEWAY_URL"]       # http://gateway:4000/v1
GATEWAY_KEY      = os.environ["GATEWAY_KEY"]        # litellm master key
HERMES_MODEL     = os.environ.get("HERMES_MODEL", "default")

agent = AIAgent(
    model=HERMES_MODEL,
    base_url=GATEWAY_URL,
    api_key=GATEWAY_KEY,
)


class InboxMessage(BaseModel):
    open_id: str
    text: str


@app.post("/inbox")
async def inbox(msg: InboxMessage):
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, agent.run_conversation, msg.text)
    async with httpx.AsyncClient(timeout=60) as client:
        await client.post(ROUTER_REPLY_URL, json={"open_id": msg.open_id, "text": response})
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
