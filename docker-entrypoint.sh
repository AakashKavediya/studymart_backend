#!/bin/sh
set -e

# Default PORT to 8000 if not set
PORT="${PORT:-8000}"

echo "Starting StudyMart FastAPI Backend on port ${PORT}..."

# Execute Uvicorn as PID 1 replacing shell so it directly receives SIGTERM / SIGINT
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" "$@"
