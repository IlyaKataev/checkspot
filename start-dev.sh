#!/bin/bash
# Запуск локального окружения для разработки

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== CheckSpot Dev ==="

# 1. PostgreSQL
echo "→ Запускаем PostgreSQL..."
docker compose up -d postgres
sleep 2

# 2. Backend
echo "→ Запускаем backend (FastAPI + Telegram bot)..."
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

sleep 3

# 3. Frontend
echo "→ Запускаем frontend (Vite)..."
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
  npm install --legacy-peer-deps
fi
npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Готово!"
echo "  Dashboard:  http://localhost:5173"
echo "  API docs:   http://localhost:8000/docs"
echo ""
echo "Нажмите Ctrl+C для остановки"

cleanup() {
  echo "Останавливаем..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  docker compose stop postgres
}
trap cleanup EXIT INT

wait
