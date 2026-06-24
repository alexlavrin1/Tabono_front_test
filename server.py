import csv
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── Paths ───────────────────────────────────────────────────────────
# app.py sets these env vars before importing us so the desktop bundle
# and the plain "uvicorn server:app" dev workflow both work.
UPLOADS_DIR  = Path(os.getenv("UPLOADS_DIR",  "uploads"))
STATIC_DIR   = Path(os.getenv("STATIC_DIR",   "static"))
ENV_FILE     = Path(os.getenv("ENV_FILE",      ".env"))
CONV_FILE    = Path(os.getenv("CONV_FILE",     "conversations.csv"))
USER_ID_FILE = Path(os.getenv("USER_ID_FILE",  "user_id"))

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

CSV_HEADERS = ["conversation_id", "timestamp", "role", "content"]

def _ensure_csv():
    if not CONV_FILE.exists():
        with open(CONV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADERS)

def _get_user_id() -> str:
    """Return a stable user ID for this installation, creating one if needed."""
    if USER_ID_FILE.exists():
        uid = USER_ID_FILE.read_text().strip()
        if uid:
            return uid
    uid = str(uuid.uuid4())
    USER_ID_FILE.write_text(uid)
    return uid

# ── Credentials (reloaded after /api/config writes them) ────────────
def _load_env():
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=True)

_load_env()

def _api_key():    return os.getenv("OPENAI_API_KEY", "")
def _workflow_id(): return os.getenv("WORKFLOW_ID", "")

# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(title="Paper Grader Assistant")


# ── Config endpoints ─────────────────────────────────────────────────

@app.get("/api/config/status")
async def config_status():
    """Tell the frontend whether credentials are present."""
    return {"configured": bool(_api_key() and _workflow_id())}


@app.post("/api/config")
async def save_config(body: dict):
    """Persist API key + workflow ID to ENV_FILE and reload env."""
    api_key     = str(body.get("api_key", "")).strip()
    workflow_id = str(body.get("workflow_id", "")).strip()

    if not api_key or not workflow_id:
        raise HTTPException(status_code=400, detail="Both api_key and workflow_id are required.")

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.write_text("")

    set_key(str(ENV_FILE), "OPENAI_API_KEY", api_key)
    set_key(str(ENV_FILE), "WORKFLOW_ID",    workflow_id)
    _load_env()
    return {"ok": True}


# ── Session ──────────────────────────────────────────────────────────

@app.post("/api/session")
async def create_session():
    """Create a ChatKit managed session for the Agent Builder workflow."""
    if not _api_key() or not _workflow_id():
        raise HTTPException(
            status_code=400,
            detail="Not configured. Please set your API key and Workflow ID first.",
        )
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            "https://api.openai.com/v1/chatkit/sessions",
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "chatkit_beta=v1",
            },
            json={
                "workflow": {"id": _workflow_id()},
                "user": _get_user_id(),
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ── File upload ───────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Save the file locally and upload to OpenAI Files API."""
    content = await file.read()

    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds the 50 MB limit.")

    safe_name = Path(file.filename).name
    local_path = UPLOADS_DIR / safe_name
    with open(local_path, "wb") as f:
        f.write(content)

    content_type = file.content_type or "application/octet-stream"
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.post(
            "https://api.openai.com/v1/files",
            headers={"Authorization": f"Bearer {_api_key()}"},
            files={"file": (safe_name, BytesIO(content), content_type)},
            data={"purpose": "user_data"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    file_data = resp.json()
    return {"file_id": file_data["id"], "filename": safe_name, "size": len(content)}


@app.get("/api/uploads")
async def list_uploads():
    files = [
        {"filename": f.name, "size": f.stat().st_size}
        for f in sorted(UPLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        if f.is_file()
    ]
    return files


# ── Conversation logging ──────────────────────────────────────────────

@app.post("/api/log/messages")
async def log_messages(body: dict):
    """Append one or more messages from a conversation exchange to the CSV."""
    conv_id  = str(body.get("conversation_id", uuid.uuid4()))
    messages = body.get("messages", [])
    if not messages:
        return {"ok": True, "written": 0}

    _ensure_csv()
    with open(CONV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for msg in messages:
            w.writerow([
                conv_id,
                msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                msg.get("role", ""),
                msg.get("content", ""),
            ])
    return {"ok": True, "written": len(messages)}


@app.get("/api/conversations.csv")
async def download_conversations():
    """Download the full conversation log as a CSV file."""
    _ensure_csv()
    return FileResponse(
        str(CONV_FILE),
        filename="conversations.csv",
        media_type="text/csv",
    )


@app.get("/api/conversations")
async def list_conversations():
    """Return all conversations grouped by ID, newest first."""
    if not CONV_FILE.exists():
        return []

    groups: dict = {}
    with open(CONV_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row.get("conversation_id", "")
            if not cid:
                continue
            if cid not in groups:
                groups[cid] = {"id": cid, "started_at": row.get("timestamp", ""), "messages": []}
            groups[cid]["messages"].append({
                "role":      row.get("role", ""),
                "content":   row.get("content", ""),
                "timestamp": row.get("timestamp", ""),
            })

    # Sort newest-first by the timestamp of the first message in each group
    result = sorted(groups.values(), key=lambda c: c["started_at"], reverse=True)
    return result


@app.get("/api/conversations/count")
async def conversation_count():
    """Return the number of logged message rows (for the UI badge)."""
    if not CONV_FILE.exists():
        return {"rows": 0}
    with open(CONV_FILE, newline="", encoding="utf-8") as f:
        rows = sum(1 for _ in csv.reader(f)) - 1  # subtract header
    return {"rows": max(rows, 0)}


# ── Static frontend — must come last ─────────────────────────────────
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
