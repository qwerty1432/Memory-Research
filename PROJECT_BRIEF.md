# Project Brief: AI Companion Research Platform

Concise context for contributors (e.g. Codex). **Day-to-day iteration is: push to git and update the Purdue server**—local dev is documented below for reference and first-time setup, but the team no longer relies on it as the primary loop.

---

## Purpose

Research chatbot platform studying how **memory persistence** and **user control** affect trust, privacy perception, and disclosure. The live study currently uses three conditions:

- `SESSION_AUTO`
- `PERSISTENT_AUTO`
- `PERSISTENT_USER`

The legacy `SESSION_USER` arm is no longer active. Existing rows from that arm should be migrated to `PERSISTENT_USER` with `backend/migrate_conditions.py`.

Participants primarily experience the study through **Qualtrics** (iframe embed). Researchers also use the **playground** (`/playground`) for testing; it hits the same backend behavior as production when sending `phase: null` (single-block mode).

---

## Stack

- **Frontend:** Next.js + React + TypeScript + Tailwind
- **Backend:** FastAPI + SQLAlchemy
- **DB:** SQLite (default local; **production server uses SQLite** under `~/data/`) or PostgreSQL if configured
- **LLM:** Purdue GenAI HTTP API (`https://genai.rcac.purdue.edu`)

---

## Workflow: what we actually use

1. Develop as needed, then **`git push`** to the main (or agreed) branch.
2. **On the server** (`hai.cs.purdue.edu`; full SSH and layout in `deploy/README.md`):
   - **`~/bin/update.sh`** — `git pull`, reinstall backend deps, rebuild frontend, restart services
   - **`~/bin/update.sh --backend-only`** / **`~/bin/update.sh --frontend-only`** when you only changed one side

**Authoritative deployment reference:** `deploy/README.md` (architecture, ports, logs, Qualtrics embed URL, troubleshooting, disk quota, database path).

**After deploy:** e.g. `curl http://127.0.0.1:8000/health`, and the frontend check used in `deploy/update.sh` (port `42800`, app base path—see server docs).

---

## Production architecture (mental model)

```
Qualtrics iframe → https://hai.cs.purdue.edu (Apache, SSL)
  → Next.js (e.g. :42800) with NEXT_PUBLIC_BASE_PATH (e.g. /study/memory-chatbot/)
      ├── static app + /api rewrites (dev) or Apache proxy (prod—see deploy/README.md)
      └── FastAPI (:8000) → SQLite (~/data/memory_research.db) → Purdue GenAI (HTTPS outbound)
```

---

## Deploy (Purdue server — summary)

Target public URL: **`https://hai.cs.purdue.edu`**. Full steps, account names, and directory layout: **`deploy/README.md`**.

Summary:

1. SSH to server and switch to the deploy account (see `deploy/README.md`).
2. First-time: run **`deploy/setup-server.sh`** flow from repo (cloned to e.g. `~/app`).
3. Configure **`~/app/backend/.env`**: `GENAI_API_KEY` or comma-separated `GENAI_API_KEYS`, `SECRET_KEY`, etc. (chat model is fixed in code: `llama4:latest`.)
4. Build frontend (production picks up **`.env.local`**): `cd ~/app/frontend && npm run build`
5. Start services: **`~/etc/rc.local start`** (stop default Apache placeholder per deploy README if applicable).
6. Verify:
   - `curl http://127.0.0.1:8000/health`
   - `curl -s http://127.0.0.1:42800 | head -20` (or URL including base path as in deploy docs)
7. **Ongoing updates:** `~/bin/update.sh` (and `--backend-only` / `--frontend-only`).

**Qualtrics iframe:** use production URL including subpath; see **`deploy/qualtrics-embed.html`** and `deploy/README.md`.

---

## Environment variables

### Backend (`backend/.env` — on server: `~/app/backend/.env`)

| Variable | Notes |
|----------|--------|
| `DATABASE_URL` | Default e.g. `sqlite:///./memory_research.db` (local); server uses path under `~/data/` per deploy layout |
| Chat model | Fixed in `backend/app/genai_client.py` as `llama4:latest` (not via env) |
| `GENAI_API_KEY` or `GENAI_API_KEYS` | Required for LLM calls; multiple keys comma-separated for round-robin / rate limits |
| `OPENAI_API_KEY` | Legacy compatibility, optional |
| `SECRET_KEY` | Set securely in non-dev (e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"`) |
| `ENVIRONMENT` | `development` vs `production` (CORS: dev allows broad origins; prod uses `ALLOWED_ORIGINS` if set) |
| `ALLOWED_ORIGINS` | Production: comma-separated origins for Qualtrics if needed (see `backend/app/main.py`) |

### Frontend (`frontend/.env.local`)

| Variable | Notes |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Default `http://localhost:8000` when not using Next rewrites |
| `NEXT_PUBLIC_ENVIRONMENT` | Default `development` |
| `NEXT_PUBLIC_BASE_PATH` | Empty locally; **set for subpath deployments** (e.g. `/study/memory-chatbot/`) |

### Prompt / study copy

- **`backend/prompt_config.json`** — phase question banks, guided system prompt, follow-up variants, skip-confirmation text, etc. Loading and optional admin overrides: **`backend/app/prompt_store.py`**, **`backend/app/routers/prompts.py`**, playground UI where applicable.

---

## Where to work in the codebase (hot paths)

| Area | Role |
|------|------|
| `backend/app/routers/chat.py` | **POST `/chat`**: single-block guided flow (`phase is None`), progress via `progress_update` events, effort follow-ups, explicit skip + ambiguous skip confirmation, `/chat/progress`, `/chat/advance` |
| `backend/app/prompt_builder.py` + `backend/prompt_config.json` | Sufficiency, follow-up generation, skip heuristics, scripted prompts |
| `backend/app/routers/auth.py` | **Qualtrics bootstrap** (`phase: null` for single-block), session + progress initialization |
| `backend/app/logging.py` | `progress_update`, `effort_check`, messages, errors—research event stream |
| `backend/app/memory_manager.py` | Condition-specific memory extraction, approval, deduplication |
| `backend/app/genai_client.py` | LLM calls, sanitization of model output |
| `frontend/app/page.tsx` | **Qualtrics** shell: URL-param auth, `phase: null`, progress header, advance button |
| `frontend/app/playground/page.tsx` | **Researcher testing**: same chat API with `phase: null`, prompt config editing |
| `frontend/components/ChatWindow.tsx` | Shared chat UI (**non-streaming** `POST /chat`) |
| `frontend/lib/api.ts` | Axios client, `qualtricsAuthenticate`, `send`, `getProgress`, `advancePhase` |

### Additional entrypoints (full list)

- Backend bootstrap: `backend/app/main.py` (CORS, routers, GenAI warmup)
- Session API: `backend/app/routers/session.py`
- Memory API: `backend/app/routers/memory.py`
- Surveys: `backend/app/routers/survey.py`
- Deployment scripts: `deploy/setup-server.sh`, `deploy/update.sh`, `deploy/rc.local`

---

## Secondary / legacy (don’t assume feature parity)

- **`POST /chat/stream`** — SSE streaming exists in `backend/app/routers/chat.py`; **current frontend only uses non-streaming `POST /chat`**. Treat streaming as optional or stale until wired in the UI.
- **Explicit `phase: 1–3` on chat requests** — “Legacy” path (e.g. estimated prompt index from message count). **Qualtrics and playground use `phase: null` (single-block)** — this is the maintained path.
- **Full registration/login flows** — still in the repo for non-Qualtrics use; **live study is Qualtrics-centric** for participants.
- Root **`README.md`** — long-form local setup and feature list; **server operations** are authoritative in **`deploy/README.md`**.

---

## Local development (reference)

When you do run locally (not the team’s primary workflow):

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # add GENAI_API_KEY / GENAI_API_KEYS
python init_db.py
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Docker Compose (optional)

```bash
docker compose up --build
```

---

## Quick verification

| Environment | Check |
|-------------|--------|
| Local frontend | `http://localhost:3000` |
| Local backend | `http://localhost:8000/health`, `http://localhost:8000/docs` |
| Server | See `deploy/README.md` and `~/bin/update.sh` health checks |

---

## Improving the project (directional)

- **Deploy & ops:** Keep `deploy/README.md` and `deploy/update.sh` aligned with production (ports, base path, account names).
- **Data & analysis:** `RESEARCH_READINESS.md` lists broader gaps (exports, dashboards, survey pipeline). Event logging exists in backend; **analysis/export** may still need work per IRB and research plan.
- **Study UX:** Single-block behavior (sufficiency, follow-up caps, skip vs clarification) is centralized in **`chat.py` + `prompt_builder`**—prefer tuning there over duplicate logic.
- **Tests:** Backend has `test_*.py` scripts; confirm CI expectations before relying on them for regressions.
- **Streaming:** If lower latency matters, **either integrate `POST /chat/stream` in the frontend** or remove dead code deliberately.

---

## Related documentation

| Doc | Contents |
|-----|----------|
| **`deploy/README.md`** | Server layout, `~/bin/update.sh`, logs, Qualtrics URL, troubleshooting—**authoritative for deployment** |
| **`deploy/qualtrics-embed.html`** | Iframe embed reference |
| **`RESEARCH_READINESS.md`** | Research/feature checklist (may be partially outdated) |
| **`README.md`** | Long-form local setup, architecture overview, feature list |

---

## Quick file map (repo-relative)

```
backend/app/main.py
backend/app/routers/chat.py
backend/app/routers/auth.py
backend/app/prompt_builder.py
backend/prompt_config.json
frontend/app/page.tsx
frontend/app/playground/page.tsx
frontend/lib/api.ts
deploy/README.md
deploy/update.sh
```
