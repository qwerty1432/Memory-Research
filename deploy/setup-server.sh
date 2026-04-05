#!/bin/bash
set -euo pipefail

#
# One-time server setup for hai.cs.purdue.edu
# Run as: hai-wiki@legion.cs.purdue.edu
# Usage:  bash ~/setup-server.sh
#

REPO_URL="https://github.com/qwerty1432/Memory-Research.git"
NODE_VERSION="v20.18.3"
NODE_TARBALL="node-${NODE_VERSION}-linux-x64.tar.xz"
NODE_URL="https://nodejs.org/dist/${NODE_VERSION}/${NODE_TARBALL}"

HOME_DIR="/homes/hai-wiki"
APP_DIR="${HOME_DIR}/app"
VENV_DIR="${HOME_DIR}/venv"
NODE_DIR="${HOME_DIR}/local/node"
DATA_DIR="${HOME_DIR}/data"
LOGS_DIR="${HOME_DIR}/logs"
RUN_DIR="${HOME_DIR}/run"
BIN_DIR="${HOME_DIR}/bin"

echo "=== AI Companion Research Platform — Server Setup ==="
echo "Home: ${HOME_DIR}"
echo ""

# ── Step 1: Create directory structure ──────────────────────────────────────
echo "[1/8] Creating directories..."
mkdir -p "${APP_DIR}" "${DATA_DIR}" "${LOGS_DIR}" "${RUN_DIR}" "${BIN_DIR}" "${HOME_DIR}/local"

# ── Step 2: Install Node.js locally ─────────────────────────────────────────
if [ -x "${NODE_DIR}/bin/node" ]; then
    echo "[2/8] Node.js already installed: $(${NODE_DIR}/bin/node --version)"
else
    echo "[2/8] Installing Node.js ${NODE_VERSION}..."
    cd /tmp
    curl -LO "${NODE_URL}"
    tar xf "${NODE_TARBALL}"
    rm -rf "${NODE_DIR}"
    mv "node-${NODE_VERSION}-linux-x64" "${NODE_DIR}"
    rm -f "${NODE_TARBALL}"
    echo "  Installed: $(${NODE_DIR}/bin/node --version)"
fi

export PATH="${NODE_DIR}/bin:${VENV_DIR}/bin:${PATH}"

# ── Step 3: Create Python virtualenv ────────────────────────────────────────
if [ -f "${VENV_DIR}/bin/activate" ]; then
    echo "[3/8] Python venv already exists."
else
    echo "[3/8] Creating Python virtualenv..."
    python3 -m venv "${VENV_DIR}"
    echo "  Created at ${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

# ── Step 4: Clone repository ────────────────────────────────────────────────
if [ -d "${APP_DIR}/.git" ]; then
    echo "[4/8] Repository already cloned. Pulling latest..."
    cd "${APP_DIR}"
    git pull
else
    echo "[4/8] Cloning repository..."
    git clone "${REPO_URL}" "${APP_DIR}"
    cd "${APP_DIR}"
fi

# ── Step 5: Install backend dependencies ────────────────────────────────────
echo "[5/8] Installing backend Python dependencies..."
cd "${APP_DIR}/backend"
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r requirements.txt

# ── Step 6: Install frontend dependencies & build ───────────────────────────
echo "[6/8] Installing frontend dependencies & building..."
cd "${APP_DIR}/frontend"
npm ci
echo "  Building Next.js for production..."
npm run build

# ── Step 7: Create .env files (only if missing) ────────────────────────────
echo "[7/8] Setting up environment files..."

if [ ! -f "${APP_DIR}/backend/.env" ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > "${APP_DIR}/backend/.env" << ENVEOF
DATABASE_URL=sqlite:////${DATA_DIR}/memory_research.db
GENAI_MODEL=gpt-oss:latest
# One key: GENAI_API_KEY=PASTE_YOUR_KEY_HERE
# Or multiple (comma-separated, round-robin): GENAI_API_KEYS=key1,key2
GENAI_API_KEY=PASTE_YOUR_KEY_HERE
SECRET_KEY=${SECRET}
ENVIRONMENT=production
ALLOWED_ORIGINS=https://hai.cs.purdue.edu,https://purdue.yul1.qualtrics.com
ENVEOF
    echo "  Created backend/.env — EDIT it: GENAI_API_KEY or GENAI_API_KEYS, optional GENAI_MODEL"
else
    echo "  backend/.env already exists (keeping current)"
fi

if [ ! -f "${APP_DIR}/frontend/.env.local" ]; then
    cat > "${APP_DIR}/frontend/.env.local" << ENVEOF
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ENVIRONMENT=production
NEXT_PUBLIC_BASE_PATH=/study/memory-chatbot
ENVEOF
    echo "  Created frontend/.env.local"
else
    echo "  frontend/.env.local already exists (keeping current)"
fi

# ── Step 8: Initialize database ─────────────────────────────────────────────
echo "[8/8] Initializing database..."
cd "${APP_DIR}/backend"
python init_db.py

# ── Install rc.local & helper scripts ───────────────────────────────────────
echo ""
echo "=== Installing rc.local and helper scripts ==="

cp "${APP_DIR}/deploy/rc.local" "${HOME_DIR}/etc/rc.local"
chmod 700 "${HOME_DIR}/etc/rc.local"
echo "  Installed rc.local"

cp "${APP_DIR}/deploy/update.sh" "${BIN_DIR}/update.sh"
chmod 755 "${BIN_DIR}/update.sh"
echo "  Installed ~/bin/update.sh"

echo ""
echo "=============================================="
echo "  Setup complete!"
echo ""
echo "  BEFORE starting services:"
echo "    1. Edit ${APP_DIR}/backend/.env"
echo "       → Set GENAI_API_KEY or GENAI_API_KEYS (comma-separated); optional GENAI_MODEL"
echo "    2. Rebuild frontend (picks up .env.local):"
echo "       cd ${APP_DIR}/frontend && npm run build"
echo ""
echo "  To start services:"
echo "    ~/etc/rc.local start"
echo ""
echo "  To check status:"
echo "    curl http://127.0.0.1:8000/health   # backend"
echo "    curl -s http://127.0.0.1:42800 | head -5  # frontend"
echo ""
echo "  Logs:"
echo "    tail -f ~/logs/backend.log"
echo "    tail -f ~/logs/frontend.log"
echo "=============================================="
