#!/bin/bash
set -e

cd "$(dirname "$0")"

# Check for .env
if [ ! -f .env ]; then
  echo "⚠  No .env file found. Copying .env.example → .env"
  cp .env.example .env
  echo "   Edit .env and add your OPENAI_API_KEY and WORKFLOW_ID, then re-run."
  exit 1
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "📦 Installing Python dependencies..."
  pip3 install -r requirements.txt
fi

echo "🚀 Starting server at http://localhost:8000"
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
