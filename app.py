"""
Desktop launcher for Paper Grader Assistant.
Starts the FastAPI server in a background thread, then opens a native
PyWebView window — no browser, no terminal needed.
"""

import os
import sys
import threading
import time
from pathlib import Path


# ── Persistent data directory (per-OS) ──────────────────────────────
# This is where .env (credentials) and uploaded files are stored
# between runs, even after the app is updated.

if sys.platform == "darwin":
    APP_DIR = Path.home() / "Library" / "Application Support" / "PaperGrader"
elif sys.platform == "win32":
    APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "PaperGrader"
else:
    APP_DIR = Path.home() / ".papergader"

APP_DIR.mkdir(parents=True, exist_ok=True)
(APP_DIR / "uploads").mkdir(exist_ok=True)


# ── Tell server.py where to find / write things ──────────────────────
os.environ["UPLOADS_DIR"]   = str(APP_DIR / "uploads")
os.environ["ENV_FILE"]      = str(APP_DIR / ".env")
os.environ["CONV_FILE"]     = str(APP_DIR / "conversations.csv")
os.environ["USER_ID_FILE"]  = str(APP_DIR / "user_id")

# When bundled by PyInstaller, static/ lives inside the temp extract dir.
if getattr(sys, "frozen", False):
    _base = Path(sys._MEIPASS)          # type: ignore[attr-defined]
else:
    _base = Path(__file__).parent

os.environ["STATIC_DIR"] = str(_base / "static")

# Load credentials from the persistent .env (if it already exists)
from dotenv import load_dotenv          # noqa: E402  (after env vars are set)
load_dotenv(APP_DIR / ".env")


# ── Server ───────────────────────────────────────────────────────────
PORT       = 8765
SERVER_URL = f"http://127.0.0.1:{PORT}"


def _run_server() -> None:
    import uvicorn
    from server import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def _wait_for_server(timeout: float = 10.0) -> bool:
    import httpx
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            httpx.get(SERVER_URL + "/api/config/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.15)
    return False


# ── Main ─────────────────────────────────────────────────────────────
def main() -> None:
    import webview  # noqa: PLC0415  (import here so the module works without webview in dev)

    # Start FastAPI in a daemon thread so it exits when the window closes
    threading.Thread(target=_run_server, daemon=True).start()

    if not _wait_for_server():
        webview.create_window(
            "Paper Grader — Error",
            html="<h2 style='font-family:sans-serif;padding:2rem;color:#c00'>"
                 "Server failed to start. Check that port 8765 is free.</h2>",
        )
        webview.start()
        return

    webview.create_window(
        "Paper Grader Assistant",
        SERVER_URL,
        width=1280,
        height=820,
        min_size=(900, 620),
        resizable=True,
        text_select=True,
    )

    # debug=False hides the browser inspector; set True while developing
    webview.start(debug=False)


if __name__ == "__main__":
    main()
