import os
import uuid
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from logging_utils import log_event

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

from memory.session_memory import get_session, clear_session
from crew import build_crew

app = FastAPI(title="Prime Bank Credit Card Assistant", version="1.0.0")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class ClearRequest(BaseModel):
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    request_id = str(uuid.uuid4())
    session_id = req.session_id or str(uuid.uuid4())
    session = get_session(session_id)
    log_event(
        "chat_request",
        request_id=request_id,
        session_id=session_id,
        message_chars=len(req.message.strip()),
    )
    response = build_crew(req.message.strip(), session, request_id=request_id)
    log_event(
        "chat_response",
        request_id=request_id,
        session_id=session_id,
        response_chars=len(response),
    )
    return ChatResponse(response=response, session_id=session_id)


@app.post("/clear")
async def clear_endpoint(req: ClearRequest):
    clear_session(req.session_id)
    log_event("session_cleared", session_id=req.session_id)
    return {"status": "ok"}


@app.get("/health")
async def health():
    log_event("health_check", model=_cfg["llm"]["model"])
    return {"status": "ok", "model": _cfg["llm"]["model"]}


@app.get("/")
async def serve_ui():
    return FileResponse("static/index.html")


if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    host = _cfg.get("server", {}).get("host", "0.0.0.0")
    port = _cfg.get("server", {}).get("port", 8000)
    uvicorn.run("api:app", host=host, port=port, reload=False, workers=1)