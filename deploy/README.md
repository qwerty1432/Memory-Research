# Deployment Guide — hai.cs.purdue.edu

## Architecture

```
Qualtrics iframe (https://purdue.yul1.qualtrics.com)
  → https://hai.cs.purdue.edu
    → system Apache (port 443, SSL termination)
      → 127.0.0.1:42800 (Next.js production server)
          ├── /*      → React frontend
          └── /api/*  → rewrite proxy → 127.0.0.1:8000
                        → FastAPI/uvicorn backend
                            → SQLite (~/data/memory_research.db)
                            → Purdue GenAI API (outbound HTTPS)
```

## Server Details

| Item | Value |
|------|-------|
| Host | `legion.cs.purdue.edu` |
| Account | `hai-wiki` (sudo from your Purdue account) |
| Home | `/homes/hai-wiki` |
| Public URL | `https://hai.cs.purdue.edu` |
| Disk quota | 5 GB |
| OS | Ubuntu 22.04 LTS |

## Prerequisites

You need to be on Purdue WiFi (or VPN) to SSH in.

```bash
ssh YOUR_PURDUE_USER@legion.cs.purdue.edu
sudo -iu hai-wiki
```

## First-Time Setup

### 1. Push code to GitHub

From your local machine:

```bash
cd ~/MemoryResearch
git add -A
git commit -m "Add deployment scripts"
git push origin main
```

### 2. Run setup script on server

```bash
ssh YOUR_PURDUE_USER@legion.cs.purdue.edu
sudo -iu hai-wiki

# Download and run setup (one command)
cd ~
curl -LO https://raw.githubusercontent.com/qwerty1432/Memory-Research/main/deploy/setup-server.sh
bash setup-server.sh
```

If the repo is private, set up HTTPS credentials first:
```bash
git config --global credential.helper store
# Then git clone will prompt for username + personal access token
```

### 3. Configure environment

Edit the backend `.env` with your actual API key:

```bash
nano ~/app/backend/.env
```

Set these values:
- `GENAI_API_KEY` → one Purdue GenAI key, **or** use multiple keys (comma-separated) to spread rate limits:  
  `GENAI_API_KEYS=sk-first,sk-second` (preferred when several researchers each have a key)
- `GENAI_MODEL` → optional; default is `gpt-oss:latest` (RCAC keeps this model hot; older models may cold-load). Override with e.g. `llama4:latest` if your project prefers it.
- `SECRET_KEY` → generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- Everything else is pre-configured

### 4. Rebuild frontend (picks up .env.local)

```bash
export PATH=$HOME/local/node/bin:$PATH
cd ~/app/frontend
npm run build
```

### 5. Stop Apache and start services

```bash
# Stop the default Apache that was serving the placeholder page
~/apache/bin/apachectl stop

# Start our services
~/etc/rc.local start
```

### 6. Verify

```bash
# Backend health check
curl http://127.0.0.1:8000/health
# → {"status":"healthy"}

# Frontend
curl -s http://127.0.0.1:42800 | head -20
# → HTML output

# From your browser (on Purdue WiFi):
# https://hai.cs.purdue.edu/
```

## Updating After Code Changes

The everyday workflow for iterating on the code:

```bash
# On your local machine:
git add -A && git commit -m "description" && git push

# On the server:
ssh YOUR_USER@legion.cs.purdue.edu
sudo -iu hai-wiki
~/bin/update.sh              # full update (pull + rebuild + restart)
~/bin/update.sh --backend-only    # skip frontend rebuild
~/bin/update.sh --frontend-only   # skip backend pip install
```

## Manual Service Management

```bash
~/etc/rc.local start      # start both services
~/etc/rc.local stop       # stop both services
~/etc/rc.local restart    # restart both
~/etc/rc.local status     # check if running
```

## Viewing Logs

```bash
tail -f ~/logs/backend.log     # FastAPI logs
tail -f ~/logs/frontend.log    # Next.js logs

# Last 100 lines
tail -100 ~/logs/backend.log
```

## Log Rotation

Logs can grow over time. To clear them:

```bash
> ~/logs/backend.log
> ~/logs/frontend.log
~/etc/rc.local restart
```

## Qualtrics iframe Update

In the Qualtrics survey builder, update the iframe embed code to point at the
production subpath `https://hai.cs.purdue.edu/study/memory-chatbot/`.

See full embed HTML in `deploy/qualtrics-embed.html`.

## Directory Layout on Server

```
/homes/hai-wiki/
├── app/                    # Git repo (cloned)
│   ├── backend/            # FastAPI application
│   │   ├── .env            # Production config (gitignored)
│   │   └── app/            # Python source
│   ├── frontend/           # Next.js application
│   │   ├── .env.local      # Production config (gitignored)
│   │   └── .next/          # Build output
│   └── deploy/             # Deployment scripts (this directory)
├── data/                   # SQLite database file
│   └── memory_research.db
├── logs/                   # Application logs
│   ├── backend.log
│   └── frontend.log
├── run/                    # PID files
│   ├── backend.pid
│   └── frontend.pid
├── local/
│   └── node/               # Node.js 20 LTS (local install)
├── venv/                   # Python virtual environment
├── bin/
│   └── update.sh           # Deployment update script
├── etc/
│   └── rc.local            # Service startup script
└── apache/                 # Original Apache (stopped, kept as backup)
```

## Troubleshooting

### Services won't start
```bash
# Check if ports are already in use
ss -tlnp | grep -E '8000|42800'

# Kill orphan processes
pkill -u hai-wiki -f uvicorn
pkill -u hai-wiki -f "next start"

# Try starting again
~/etc/rc.local start
```

### Frontend shows 502 / can't reach backend
```bash
# Is backend actually running?
curl http://127.0.0.1:8000/health

# Check backend logs for errors
tail -50 ~/logs/backend.log
```

### GenAI API errors
```bash
# Test connectivity from server
curl -sI https://genai.rcac.purdue.edu

# Check keys / model are set (do not paste keys in chat)
grep -E 'GENAI_API_KEY|GENAI_API_KEYS|GENAI_MODEL' ~/app/backend/.env
```

Each outbound GenAI call uses the next key in round-robin when multiple keys are configured. Per-key rate limits (e.g. 200/min) apply separately to each key.

### Database issues
```bash
# Check database exists and is readable
ls -la ~/data/memory_research.db

# Re-initialize if needed
source ~/venv/bin/activate
cd ~/app/backend
python init_db.py
```

### Disk quota
```bash
quota -s
du -sh ~/app ~/venv ~/local ~/data ~/logs
```

## Server Reboots

The server reboots ~once per quarter for security updates. When it does, it automatically runs `~/etc/rc.local start`, which starts both services. No manual intervention needed.
