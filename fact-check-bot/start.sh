#!/bin/bash
set -e

echo "Starting Fact-Check Bot..."

# Start backend (FastAPI)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend (Next.js)
cd frontend && npm start -- -p 3000 &
FRONTEND_PID=$!

echo "Backend running on :8000, Frontend running on :3000"

# Wait for either process to exit
wait -n $BACKEND_PID $FRONTEND_PID
exit $?
