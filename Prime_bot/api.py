import os
import uuid
import yaml
import time
import json
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from logging_utils import log_event

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

from memory.session_memory import get_session, clear_session
from crew import build_crew_stream

app = FastAPI(title="Prime Bank Credit Card Assistant", version="1.0.0")


def _warmup_model() -> None:
    try:
        from llm.ollama_client import chat as llm_chat
        started = time.perf_counter()
        llm_chat(
            messages=[{"role": "user", "content": "warmup"}],
            system="Reply with OK.",
            temperature=0.0,
            max_tokens=1,
            think=False,
        )
        log_event("llm_warmup_complete", latency_ms=round((time.perf_counter() - started) * 1000, 2))
    except Exception as e:
        log_event("llm_warmup_error", level="error", error=str(e))


class ClearRequest(BaseModel):
    session_id: str


@app.on_event("startup")
async def startup_event():
    if _cfg.get("llm", {}).get("warmup_on_start", True):
        thread = threading.Thread(target=_warmup_model, daemon=True)
        thread.start()
        log_event("llm_warmup_started")


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    session_id: str | None = None
    log_event("ws_connected")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "clear":
                sid = data.get("session_id") or session_id
                if sid:
                    clear_session(sid)
                    log_event("session_cleared", session_id=sid)
                session_id = None
                await websocket.send_text(json.dumps({"type": "cleared"}))
                continue

            if msg_type != "message":
                await websocket.send_text(json.dumps({"type": "error", "message": f"Unknown type: {msg_type}"}))
                continue

            message = (data.get("message") or "").strip()
            if not message:
                await websocket.send_text(json.dumps({"type": "error", "message": "Message cannot be empty."}))
                continue

            if not session_id:
                session_id = data.get("session_id") or str(uuid.uuid4())

            session = get_session(session_id)
            request_id = str(uuid.uuid4())

            log_event("ws_chat_request", request_id=request_id, session_id=session_id, message_chars=len(message))
            await websocket.send_text(json.dumps({"type": "session_id", "session_id": session_id}))

            try:
                for token in build_crew_stream(message, session, request_id=request_id):
                    await websocket.send_text(json.dumps({"type": "token", "token": token}))
                await websocket.send_text(json.dumps({"type": "done"}))
                log_event("ws_chat_complete", request_id=request_id, session_id=session_id)

            except Exception as e:
                log_event("ws_stream_error", request_id=request_id, session_id=session_id, error=str(e))
                await websocket.send_text(json.dumps({"type": "error", "message": "Stream error. Please try again."}))

    except WebSocketDisconnect:
        log_event("ws_disconnected", session_id=session_id)


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