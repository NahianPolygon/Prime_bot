import os
import uuid
import yaml
import time
import json
import secrets
import threading
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from logging_utils import log_event
from streaming_utils import iter_text_stream
from ingestion.company_ingest import BANKING_TYPES, DOCUMENT_TYPES, ingest_company_text, ingest_markdown_path
from kb_runtime import (
    BANKING_TYPES as RUNTIME_BANKING_TYPES,
    build_collection_map,
    get_active_bank,
    load_runtime_state,
    save_runtime_state,
    slugify_bank,
)

_stats_lock = threading.Lock()
_stats = {
    "total_requests": 0,
    "total_eligibility_forms": 0,
    "total_errors": 0,
    "latency_ms_sum": 0.0,
    "latency_count": 0,
    "unique_sessions": set(),
}


async def _send_text_stream(websocket: WebSocket, text: str, chunk_chars: int = 24, delay_ms: int = 14):
    for chunk in iter_text_stream(text, chunk_chars=chunk_chars):
        await websocket.send_text(json.dumps({"type": "token", "token": chunk}))
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)


async def _send_progress(websocket: WebSocket, message: str, stage: str = ""):
    await websocket.send_text(json.dumps({
        "type": "progress",
        "message": message,
        "stage": stage,
    }))
    await asyncio.sleep(0.02)


def _infer_eligibility_outcome(text: str) -> str:
    rl = (text or "").lower()
    if "\u274c" in text or "likely ineligible" in rl or "not eligible" in rl or "ineligible" in rl:
        return "ineligible"
    if "\u26a0\ufe0f" in text or "borderline" in rl or "conditional" in rl:
        return "borderline"
    if "\u2705" in text or "likely eligible" in rl:
        return "eligible"
    return "general"


def _infer_eligibility_outcome_from_verdicts(verdicts: list[dict]) -> str:
    if not verdicts:
        return "general"

    statuses = {str(item.get("status", "")).lower() for item in verdicts}
    if statuses == {"eligible"}:
        return "eligible"
    if statuses == {"ineligible"}:
        return "ineligible"
    if "borderline" in statuses or ({"eligible", "ineligible"} & statuses and len(statuses) > 1):
        return "borderline"
    if "eligible" in statuses:
        return "eligible"
    if "ineligible" in statuses:
        return "ineligible"
    return "general"


def _record_request(session_id: str):
    with _stats_lock:
        _stats["total_requests"] += 1
        _stats["unique_sessions"].add(session_id)


def _record_latency(ms: float):
    with _stats_lock:
        _stats["latency_ms_sum"] += ms
        _stats["latency_count"] += 1


def _record_error():
    with _stats_lock:
        _stats["total_errors"] += 1


def _record_eligibility():
    with _stats_lock:
        _stats["total_eligibility_forms"] += 1

with open("config.yaml") as f:
    _cfg = yaml.safe_load(f)

from memory.session_memory import get_session, clear_session
from chat_flow import build_crew_stream, handle_eligibility_form, handle_preference_form, clear_preference_session
from agents.compliance_faq import extract_target_card, get_eligibility_form_schema

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


class KnowledgeBaseUploadRequest(BaseModel):
    company_name: str = ""
    bank_name: str = ""
    document_title: str
    raw_text: str
    document_type: str
    banking_type: str = "both"
    product_name: str = ""
    card_network: str = ""
    tier: str = ""
    source: str = ""
    use_cases: list[str] = Field(default_factory=list)
    employment_suitable: list[str] = Field(default_factory=list)
    replace_existing: bool = True


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class RuntimeKnowledgeBaseStateRequest(BaseModel):
    active_bank: str


class BankCreateRequest(BaseModel):
    bank_name: str


class MarkdownUpdateRequest(BaseModel):
    path: str
    content: str


ADMIN_USERNAME = "NahianPolygon"
ADMIN_PASSWORD = "123456"
ADMIN_TOKEN = "primebot-admin-token"
PROJECT_ROOT = Path(".").resolve()
BANKS_ROOT = (PROJECT_ROOT / "banks").resolve()


def _require_admin(authorization: str = Header(default="")) -> None:
    expected = f"Bearer {ADMIN_TOKEN}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Admin authentication required.")


def _ensure_active_bank_dirs(bank_slug: str) -> None:
    for banking_type in ("conventional", "islami"):
        for document_type in DOCUMENT_TYPES:
            (Path("banks") / bank_slug / banking_type / "credit" / document_type).mkdir(parents=True, exist_ok=True)


def _list_bank_dirs() -> list[str]:
    root = Path("banks")
    if not root.exists():
        return []
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def _relative_markdown_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _resolve_active_markdown_path(path_value: str) -> Path:
    active_root = (BANKS_ROOT / get_active_bank()).resolve()
    candidate = (PROJECT_ROOT / path_value).resolve()
    if candidate.suffix != ".md":
        raise HTTPException(status_code=400, detail="Only markdown files can be edited.")
    try:
        candidate.relative_to(active_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="File is outside the active bank workspace.") from exc
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Markdown file not found.")
    return Path(_relative_markdown_path(candidate))


def _list_active_markdown_files() -> list[dict]:
    active_bank = get_active_bank()
    root = Path("banks") / active_bank
    files = []
    if not root.exists():
        return files
    for path in sorted(root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
        parts = path.parts
        banking_type = parts[2] if len(parts) > 2 else ""
        document_type = parts[4] if len(parts) > 4 else ""
        heading = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
        files.append({
            "path": str(path),
            "name": path.name,
            "title": heading or path.stem,
            "banking_type": banking_type,
            "document_type": document_type,
            "size": path.stat().st_size,
            "updated_at": path.stat().st_mtime,
        })
    return files


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
                    clear_preference_session(sid)
                    log_event("session_cleared", session_id=sid)
                session_id = None
                await websocket.send_text(json.dumps({"type": "cleared"}))
                continue

            if msg_type == "preference_form_submit":
                if not session_id:
                    session_id = data.get("session_id") or str(uuid.uuid4())

                session = get_session(session_id)
                request_id = str(uuid.uuid4())
                form_data = data.get("form_data", {})

                log_event(
                    "ws_preference_form",
                    request_id=request_id,
                    session_id=session_id,
                    banking_type=form_data.get("banking_type", ""),
                    use_case=form_data.get("use_case", ""),
                )

                await websocket.send_text(json.dumps({
                    "type": "session_id",
                    "session_id": session_id,
                }))
                await _send_progress(websocket, "Finding suitable cards", "preference_form")

                try:
                    result = handle_preference_form(form_data, session, request_id=request_id)
                    await _send_progress(websocket, "Preparing answer", "response")
                    await _send_text_stream(websocket, result)
                    await websocket.send_text(json.dumps({"type": "done", "intent": "i_need_a_credit_card", "calculator": ""}))
                    log_event("ws_preference_complete", request_id=request_id, session_id=session_id)
                except Exception as e:
                    log_event("ws_preference_error", request_id=request_id, session_id=session_id, error=str(e))
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Card recommendation failed. Please try again.",
                    }))
                continue

            if msg_type == "eligibility_form_submit":
                if not session_id:
                    session_id = data.get("session_id") or str(uuid.uuid4())

                session = get_session(session_id)
                request_id = str(uuid.uuid4())
                form_data = data.get("form_data", {})

                _record_eligibility()
                log_event(
                    "ws_eligibility_form",
                    request_id=request_id,
                    session_id=session_id,
                    target_card=form_data.get("target_card", ""),
                )

                await websocket.send_text(json.dumps({
                    "type": "session_id",
                    "session_id": session_id,
                }))
                await _send_progress(websocket, "Checking eligibility details", "eligibility_form")

                try:
                    result = handle_eligibility_form(form_data, session, request_id=request_id)
                    verdicts = session.user_profile.get("last_eligibility_verdicts") or []
                    summary = session.user_profile.get("last_eligibility_summary") or ""
                    if isinstance(verdicts, list) and verdicts:
                        elig_outcome = _infer_eligibility_outcome_from_verdicts(verdicts)
                        await websocket.send_text(json.dumps({
                            "type": "eligibility_verdicts",
                            "summary": summary,
                            "items": verdicts,
                        }))
                    else:
                        elig_outcome = _infer_eligibility_outcome(result)
                        await _send_progress(websocket, "Preparing answer", "response")
                        await _send_text_stream(websocket, result)
                    await websocket.send_text(json.dumps({"type": "done", "intent": elig_outcome, "calculator": ""}))
                    log_event(
                        "ws_eligibility_complete",
                        request_id=request_id,
                        session_id=session_id,
                        outcome=elig_outcome,
                        verdict_count=len(verdicts) if isinstance(verdicts, list) else 0,
                    )
                except Exception as e:
                    log_event(
                        "ws_eligibility_error",
                        request_id=request_id,
                        session_id=session_id,
                        error=str(e),
                    )
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Eligibility check failed. Please try again.",
                    }))
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

            _record_request(session_id)
            log_event("ws_chat_request", request_id=request_id, session_id=session_id, message_chars=len(message))
            await websocket.send_text(json.dumps({"type": "session_id", "session_id": session_id}))

            req_start = time.perf_counter()
            try:
                await _send_progress(websocket, "Understanding your request", "classify")
                done_intent = ""
                done_calculator = ""
                done_calculator_config = None
                for token in build_crew_stream(message, session, request_id=request_id):
                    if token.startswith('{"__progress_signal__"'):
                        try:
                            signal = json.loads(token)
                            if signal.get("__progress_signal__"):
                                await _send_progress(
                                    websocket,
                                    signal.get("message", "Preparing answer"),
                                    signal.get("stage", ""),
                                )
                                continue
                        except json.JSONDecodeError:
                            pass

                    if token.startswith('{"__preference_form_signal__"'):
                        try:
                            signal = json.loads(token)
                            if signal.get("__preference_form_signal__"):
                                await websocket.send_text(json.dumps({
                                    "type": "show_preference_form",
                                    "schema": signal["schema"],
                                }))
                                continue
                        except json.JSONDecodeError:
                            pass

                    if token.startswith('{"__form_signal__"'):
                        try:
                            signal = json.loads(token)
                            if signal.get("__form_signal__"):
                                await websocket.send_text(json.dumps({
                                    "type": "show_eligibility_form",
                                    "schema": signal["schema"],
                                }))
                                continue
                        except json.JSONDecodeError:
                            pass

                    if token.startswith('{"__done_signal__"'):
                        try:
                            sig = json.loads(token)
                            done_intent = sig.get("intent", "")
                            done_calculator = sig.get("calculator", "")
                            done_calculator_config = sig.get("calculator_config")
                        except json.JSONDecodeError:
                            pass
                        continue

                    await websocket.send_text(json.dumps({"type": "token", "token": token}))

                _record_latency((time.perf_counter() - req_start) * 1000)
                done_payload = {"type": "done", "intent": done_intent, "calculator": done_calculator}
                if done_calculator_config:
                    done_payload["calculator_config"] = done_calculator_config
                await websocket.send_text(json.dumps(done_payload))
                log_event("ws_chat_complete", request_id=request_id, session_id=session_id)

            except Exception as e:
                _record_error()
                log_event("ws_stream_error", request_id=request_id, session_id=session_id, error=str(e))
                await websocket.send_text(json.dumps({"type": "error", "message": "Stream error. Please try again."}))

    except WebSocketDisconnect:
        log_event("ws_disconnected", session_id=session_id)


@app.get("/analytics")
async def analytics():
    with _stats_lock:
        count = _stats["latency_count"]
        avg_latency = round(_stats["latency_ms_sum"] / count, 1) if count else 0.0
        error_rate = round(_stats["total_errors"] / _stats["total_requests"], 4) if _stats["total_requests"] else 0.0
        return {
            "total_requests": _stats["total_requests"],
            "total_eligibility_forms": _stats["total_eligibility_forms"],
            "total_errors": _stats["total_errors"],
            "error_rate": error_rate,
            "avg_latency_ms": avg_latency,
            "unique_sessions": len(_stats["unique_sessions"]),
        }


@app.get("/health")
async def health():
    log_event("health_check", model=_cfg["llm"]["model"])
    return {"status": "ok", "model": _cfg["llm"]["model"]}


@app.post("/admin/login")
async def admin_login(payload: AdminLoginRequest):
    if not secrets.compare_digest(payload.username, ADMIN_USERNAME) or not secrets.compare_digest(payload.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")
    return {"token": ADMIN_TOKEN}


@app.get("/admin/kb/state")
async def admin_kb_state(authorization: str = Header(default="")):
    _require_admin(authorization)
    return {
        **load_runtime_state(),
        "banks": _list_bank_dirs(),
        "document_types": sorted(DOCUMENT_TYPES),
        "banking_types": sorted(RUNTIME_BANKING_TYPES),
        "files": _list_active_markdown_files(),
    }


@app.post("/admin/kb/state")
async def update_admin_kb_state(
    payload: RuntimeKnowledgeBaseStateRequest,
    authorization: str = Header(default=""),
):
    _require_admin(authorization)
    bank_slug = slugify_bank(payload.active_bank)
    state = save_runtime_state({
        "active_bank": bank_slug,
        "collections": build_collection_map(bank_slug),
    })
    _ensure_active_bank_dirs(bank_slug)
    try:
        from kb_config import refresh_collection_map
        refresh_collection_map()
    except Exception:
        pass
    log_event("kb_runtime_state_updated", bank=bank_slug)
    return {
        **state,
        "banks": _list_bank_dirs(),
        "files": _list_active_markdown_files(),
    }


@app.post("/admin/kb/banks")
async def create_admin_bank(
    payload: BankCreateRequest,
    authorization: str = Header(default=""),
):
    _require_admin(authorization)
    if not (payload.bank_name or "").strip():
        raise HTTPException(status_code=400, detail="Bank name is required.")
    bank_slug = slugify_bank(payload.bank_name)
    _ensure_active_bank_dirs(bank_slug)
    log_event("kb_bank_created", bank=bank_slug)
    return {
        "bank": bank_slug,
        "banks": _list_bank_dirs(),
    }


@app.get("/kb/studio/context")
async def kb_studio_context():
    return {
        **load_runtime_state(),
        "document_types": sorted(DOCUMENT_TYPES),
        "banking_types": sorted(RUNTIME_BANKING_TYPES),
        "files": _list_active_markdown_files(),
    }


@app.get("/kb/studio/file")
async def kb_studio_file(path: str):
    md_path = _resolve_active_markdown_path(path)
    return {
        "path": str(md_path),
        "content": md_path.read_text(encoding="utf-8"),
    }


@app.put("/kb/studio/file")
async def update_kb_studio_file(payload: MarkdownUpdateRequest):
    md_path = _resolve_active_markdown_path(payload.path)
    md_path.write_text(payload.content, encoding="utf-8")
    try:
        ingest_result = ingest_markdown_path(md_path, replace_existing=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log_event("kb_markdown_update_error", level="error", path=str(md_path), error=str(exc))
        raise HTTPException(status_code=500, detail="Markdown saved, but ingestion failed.") from exc
    log_event("kb_markdown_updated", path=str(md_path), collections=ingest_result.get("collections", []))
    return {
        "path": str(md_path),
        "ingestion": ingest_result,
        "files": _list_active_markdown_files(),
    }


@app.get("/admin/kb/options")
async def kb_options():
    return {
        "document_types": sorted(DOCUMENT_TYPES),
        "banking_types": sorted(BANKING_TYPES),
        "active_bank": get_active_bank(),
    }


@app.post("/admin/kb/ingest-text")
async def kb_ingest_text(payload: KnowledgeBaseUploadRequest):
    bank_name = get_active_bank()
    banking_type = payload.banking_type
    try:
        result = ingest_company_text(
            company_name=bank_name,
            document_title=payload.document_title,
            raw_text=payload.raw_text,
            document_type=payload.document_type,
            banking_type=banking_type,
            product_name=payload.product_name,
            card_network=payload.card_network,
            tier=payload.tier,
            source=payload.source,
            use_cases=payload.use_cases,
            employment_suitable=payload.employment_suitable,
            replace_existing=payload.replace_existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log_event("kb_ingest_error", level="error", error=str(exc))
        raise HTTPException(status_code=500, detail="Knowledge base ingestion failed.") from exc

    log_event(
        "kb_ingest_complete",
        bank=result.get("bank_slug") or result["company_slug"],
        document_type=result["document_type"],
        banking_type=result["banking_type"],
        chunk_count=result["chunk_count"],
        collections=result["collections"],
        markdown_paths=result.get("markdown_paths", []),
    )
    return result


@app.get("/")
async def serve_ui():
    return FileResponse("static/index.html")


@app.get("/kb-uploader")
async def serve_kb_uploader():
    return FileResponse("static/kb_studio.html")


@app.get("/kb-studio")
async def serve_kb_studio():
    return FileResponse("static/kb_studio.html")


@app.get("/admin")
async def serve_admin():
    return FileResponse("static/admin.html")


if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    host = _cfg.get("server", {}).get("host", "0.0.0.0")
    port = _cfg.get("server", {}).get("port", 8000)
    uvicorn.run("api:app", host=host, port=port, reload=False, workers=1)
