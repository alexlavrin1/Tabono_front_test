#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# build_app.sh  –  Build "Paper Grader.app" for macOS
#
# Josh gets the finished .zip — he just unzips and double-clicks.
# Run this on YOUR Mac once.
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

APP_NAME="Paper Grader"

# ── Prerequisite: Xcode Command Line Tools ────────────────────────────────────
# PyInstaller needs lipo, install_name_tool, and codesign.
# All three are unavailable if CLT is missing or corrupted.
if ! xcrun --find lipo > /dev/null 2>&1; then
  echo ""
  echo "❌  Xcode Command Line Tools are missing or broken."
  echo ""
  echo "   Fix (one-time, ~5 minutes):"
  echo "   1. Open Terminal"
  echo "   2. Run:  sudo rm -rf /Library/Developer/CommandLineTools"
  echo "   3. Run:  xcode-select --install"
  echo "   4. Click 'Install' in the dialog and wait for it to finish"
  echo "   5. Then run this script again: bash build_app.sh"
  echo ""
  exit 1
fi

# ── Python venv ───────────────────────────────────────────────────────────────
if [ ! -f ".venv/bin/python3" ]; then
  echo "📦 Creating Python 3.11 venv…"
  python3.11 -m venv .venv
fi

echo "📦 Installing/updating dependencies…"
.venv/bin/pip install --quiet -r requirements.txt

# ── Build ─────────────────────────────────────────────────────────────────────
echo "🔨 Building ${APP_NAME}.app with PyInstaller…"

.venv/bin/pyinstaller app.py \
  --name "${APP_NAME}" \
  --windowed \
  --noconfirm \
  --clean \
  --add-data "static:static" \
  --collect-all webview \
  --collect-all uvicorn \
  --hidden-import "server" \
  --hidden-import "fastapi" \
  --hidden-import "fastapi.staticfiles" \
  --hidden-import "starlette" \
  --hidden-import "starlette.staticfiles" \
  --hidden-import "starlette.middleware" \
  --hidden-import "anyio" \
  --hidden-import "anyio._backends._asyncio" \
  --hidden-import "httpx" \
  --hidden-import "multipart" \
  --hidden-import "multipart.multipart" \
  --hidden-import "dotenv" \
  --osx-bundle-identifier "com.papergader.app"

# ── Zip for distribution ──────────────────────────────────────────────────────
echo "📦 Zipping for distribution…"
cd dist
zip -r --quiet "../${APP_NAME}.zip" "${APP_NAME}.app"
cd ..

SIZE=$(du -sh "${APP_NAME}.zip" | cut -f1)
echo ""
echo "✅  Done!  →  ${APP_NAME}.zip  (${SIZE})"
echo ""
echo "📋  Send to Josh:"
echo "   1. Send '${APP_NAME}.zip'"
echo "   2. Josh unzips it"
echo "   3. Right-click '${APP_NAME}.app' → Open → Open  (first time only — Gatekeeper)"
echo "   4. He enters his OpenAI API key + Workflow ID when prompted"
echo "   5. Done — opens automatically every time after that"
