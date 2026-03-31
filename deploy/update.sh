#!/bin/bash
set -euo pipefail

#
# Update & redeploy after code changes
# Usage: ~/bin/update.sh [--backend-only | --frontend-only | --full]
#
# Default (no flag): pulls code, rebuilds frontend, restarts both services
#

HOME_DIR="/homes/hai-wiki"
APP_DIR="${HOME_DIR}/app"
RC_LOCAL="${HOME_DIR}/etc/rc.local"

export PATH="${HOME_DIR}/local/node/bin:${HOME_DIR}/venv/bin:${HOME_DIR}/bin:${PATH}"
source "${HOME_DIR}/venv/bin/activate"

MODE="${1:---full}"

echo "=== Updating AI Companion Research Platform ==="
echo "Mode: ${MODE}"
echo ""

# ── Pull latest code ────────────────────────────────────────────────────────
echo "[1] Pulling latest code..."
cd "${APP_DIR}"
git pull
echo ""

case "${MODE}" in
    --backend-only)
        echo "[2] Reinstalling backend dependencies..."
        cd "${APP_DIR}/backend"
        pip install -r requirements.txt -q

        echo "[3] Restarting backend..."
        "${RC_LOCAL}" stop
        sleep 1
        "${RC_LOCAL}" start
        ;;

    --frontend-only)
        echo "[2] Rebuilding frontend..."
        cd "${APP_DIR}/frontend"
        npm ci --prefer-offline
        npm run build

        echo "[3] Restarting services..."
        "${RC_LOCAL}" stop
        sleep 1
        "${RC_LOCAL}" start
        ;;

    --full|*)
        echo "[2] Installing backend dependencies..."
        cd "${APP_DIR}/backend"
        pip install -r requirements.txt -q

        echo "[3] Rebuilding frontend..."
        cd "${APP_DIR}/frontend"
        npm ci --prefer-offline
        npm run build

        echo "[4] Restarting services..."
        "${RC_LOCAL}" stop
        sleep 1
        "${RC_LOCAL}" start
        ;;
esac

echo ""
echo "=== Update complete ==="
sleep 3

echo ""
echo "Checking health..."
if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "  Backend:  OK"
else
    echo "  Backend:  FAILED — check ~/logs/backend.log"
fi
if curl -sf http://127.0.0.1:42800/study/memory-chatbot/ > /dev/null 2>&1; then
    echo "  Frontend: OK"
else
    echo "  Frontend: FAILED — check ~/logs/frontend.log"
fi

"${RC_LOCAL}" status
