# AI Companion Research Platform

A web-based chatbot designed to study how AI memory persistence and user control affect user interaction and perception. This platform implements a 2×2 factorial experimental design to investigate the effects of memory persistence (session vs. persistent) and user control (automatic vs. user-controlled) on user trust, privacy, and disclosure.

## Architecture

- **Frontend**: Next.js + React + TypeScript + TailwindCSS
- **Backend**: FastAPI (Python 3.9+)
- **Database**: PostgreSQL (production) or SQLite (local development)
- **LLM**: Purdue GenAI API (Llama 3.1 model)

## Experimental Conditions

The platform implements a 2×2 factorial design with four experimental conditions:

1. **SESSION_AUTO** (Session + Automatic): Memory lasts only for one chat session, automatically extracted
2. **SESSION_USER** (Session + User-Controlled): User selects items to save, but memory resets after session
3. **PERSISTENT_AUTO** (Persistent + Automatic): All memories automatically stored and persist across sessions
4. **PERSISTENT_USER** (Persistent + User-Controlled): User approves which memories persist across sessions

## Quick Start

### Prerequisites

- Python 3.9+ 
- Node.js 18+
- pip (Python package manager)
- npm (Node package manager)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd MemoryResearch
   ```

#### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GENAI_API_KEY (required)
   # Get API key from: https://genai.rcac.purdue.edu
   ```

5. **Initialize database:**
   ```bash
   python init_db.py
   ```

6. **Run the server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

The backend will be available at http://localhost:8000

#### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env.local
   # Edit .env.local if needed (defaults work for local dev)
   ```

4. **Run development server:**
   ```bash
   npm run dev
   ```

The frontend will be available at http://localhost:3000


## Key Features

- ✅ **User Authentication**: Secure registration and login system
- ✅ **Chat Interface**: Real-time chat with AI companion using Server-Sent Events (SSE) for streaming responses
- ✅ **Experimental Conditions**: Four distinct memory conditions (2×2 factorial design)
- ✅ **Memory Management**: 
  - Automatic memory extraction from conversations
  - User-controlled memory approval/rejection/editing (for user-controlled conditions)
  - Memory deduplication to prevent duplicates
- ✅ **Session Management**: Create new sessions, view history, and manage conversation context
- ✅ **Memory Review Panel**: Review, edit, approve, or delete memory candidates (user-controlled modes)
- ✅ **Survey System**: Mid-conversation checkpoint surveys with custom forms
- ✅ **Event Logging**: Comprehensive logging of all user interactions for research data collection
- ✅ **Developer Mode**: Toggle between experimental conditions for testing (development only)
- ✅ **Tutorial System**: First-login tutorial to guide new users

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

### Backend (.env)

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | Database connection string. Use SQLite for local dev, PostgreSQL for production | No | `sqlite:///./memory_research.db` |
| `GENAI_API_KEY` | Purdue GenAI API key. Get from https://genai.rcac.purdue.edu | **Yes** | - |
| `SECRET_KEY` | Secret key for session management. Generate a random string for production | No | - |
| `ENVIRONMENT` | Environment mode: `development` or `production` | No | `development` |

**Example `.env` file:**
```bash
DATABASE_URL=sqlite:///./memory_research.db
GENAI_API_KEY=sk-your-api-key-here
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
```

### Frontend (.env.local)

Copy `frontend/.env.example` to `frontend/.env.local` and configure:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | No | `http://localhost:8000` |
| `NEXT_PUBLIC_ENVIRONMENT` | Environment mode: `development` or `production` | No | `development` |

**Example `.env.local` file:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
```

## Utility Scripts

The backend includes several utility scripts for testing and debugging. All scripts should be run from the `backend/` directory with the virtual environment activated.

### List Users and Sessions

View users and their sessions:

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate

# List all users with their sessions
python list_users.py

# Get detailed info for a specific user (by username)
python list_users.py kabeer

# Get detailed info for a specific user (by user_id)
python list_users.py 3283335e-9fe1-4121-869c-40d7b2c259a8
```

**Use cases:**
- Finding user IDs and session IDs for testing
- Checking user conditions and session status
- Viewing message counts per session
- Debugging database issues

### Test Chat Endpoint

Test the chat API directly:

```bash
cd backend
source venv/bin/activate
python test_chat_endpoint.py <user_id> <session_id> "Your message here"
```

### Test GenAI API

Test the GenAI API connection:

```bash
cd backend
source venv/bin/activate
python test_genai.py
```

### Diagnose API Issues

If you're getting "Response unavailable" errors, run the diagnostic script:

```bash
cd backend
source venv/bin/activate
python diagnose_api.py
```

**Checks performed:**
- API key configuration
- Network connectivity
- API endpoint accessibility
- Response format validation

## Troubleshooting

### "Response unavailable" Error

If you're getting "Response unavailable" when chatting:

1. **Verify backend is running:**
   - Backend should be running on `http://localhost:8000`
   - Check the terminal where you started `uvicorn` for error messages
   - Look for "GenAI API Error" in the console output

2. **Check API key:**
   - Verify `GENAI_API_KEY` is set in `backend/.env`
   - Run `python diagnose_api.py` to test the key
   - Common issues: expired key, wrong key, missing key
   - **Important**: After updating `.env`, restart the backend server

3. **Check network connectivity:**
   - Ensure you can reach `https://genai.rcac.purdue.edu`
   - Check for firewall/proxy issues
   - Verify API endpoint is accessible from your network

4. **View detailed errors:**
   - Backend errors are printed to console when running `uvicorn`
   - Check the terminal where the backend is running
   - Errors are also logged to the database (check `events` table with type `error_chat_api`)

### Database Issues

- **SQLite database locked**: Make sure only one instance of the backend is running
- **Migration errors**: Run `python init_db.py` to recreate the database schema
- **Connection errors**: Check `DATABASE_URL` in `backend/.env`

### Frontend Not Connecting to Backend

- Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches your backend URL
- Check CORS settings in `backend/app/main.py` if accessing from a different origin
- Ensure backend is running before starting the frontend

## Project Structure

```
MemoryResearch/
├── backend/                 # FastAPI backend application
│   ├── app/                # Main application code
│   │   ├── routers/        # API endpoint routes
│   │   │   ├── auth.py     # Authentication endpoints
│   │   │   ├── chat.py     # Chat endpoints
│   │   │   ├── memory.py   # Memory management endpoints
│   │   │   ├── session.py  # Session management endpoints
│   │   │   ├── condition.py # Condition management endpoints
│   │   │   └── survey.py   # Survey endpoints
│   │   ├── models.py       # SQLAlchemy database models
│   │   ├── schemas.py      # Pydantic data schemas
│   │   ├── memory_manager.py # Memory management logic
│   │   ├── prompt_builder.py # LLM prompt construction
│   │   ├── genai_client.py # GenAI API client
│   │   ├── auth.py         # Authentication utilities
│   │   ├── logging.py      # Event logging utilities
│   │   └── main.py        # FastAPI application entry point
│   ├── alembic/            # Database migrations
│   ├── .env.example        # Environment variables template
│   ├── requirements.txt    # Python dependencies
│   ├── init_db.py          # Database initialization script
│   ├── list_users.py       # Utility: List users and sessions
│   ├── test_chat_endpoint.py # Utility: Test chat API
│   ├── test_genai.py       # Utility: Test GenAI API
│   └── diagnose_api.py     # Utility: Diagnose API issues
├── frontend/               # Next.js frontend application
│   ├── app/               # Next.js app directory
│   │   ├── page.tsx       # Main chat page
│   │   ├── login/         # Login/registration page
│   │   ├── survey/        # Survey page
│   │   ├── layout.tsx     # Root layout
│   │   └── globals.css    # Global styles
│   ├── components/        # React components
│   │   ├── ChatWindow.tsx # Main chat interface
│   │   ├── MemoryReviewPanel.tsx # Memory review UI
│   │   ├── ConditionBanner.tsx # Condition display
│   │   ├── CheckpointSurvey.tsx # Survey form
│   │   ├── CollapsibleButtonMenu.tsx # Navigation menu
│   │   ├── MenuTutorial.tsx # Menu tutorial
│   │   ├── ChatTutorial.tsx # Chat tutorial
│   │   └── QuestionTypes/ # Survey question components
│   ├── lib/               # Utilities
│   │   ├── api.ts         # API client
│   │   └── storage.ts     # LocalStorage utilities
│   ├── .env.example       # Environment variables template
│   └── package.json       # Node.js dependencies
├── README.md              # This file
└── RESEARCH_READINESS.md  # Research readiness checklist
```

## API Documentation

Once the backend is running, interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login
- `POST /chat/stream` - Stream chat response (SSE)
- `GET /memory/candidates/{user_id}/{session_id}` - Get memory candidates
- `POST /memory/{memory_id}/approve` - Approve a memory
- `POST /session` - Create a new session
- `GET /survey/template/{survey_type}` - Get survey template
- `POST /survey/submit` - Submit survey responses

## Developer Mode

In development, you can access developer mode to toggle between experimental conditions:

1. Click the "Dev" button in the bottom right corner
2. Enter password: `dev123` (or automatically enabled in development)
3. Select a different condition to test

**Note**: Developer mode is only available when `NEXT_PUBLIC_ENVIRONMENT=development`

## Database Schema

The platform uses the following main tables:
- **users**: User accounts and authentication
- **sessions**: Chat sessions
- **messages**: All chat messages (permanently stored)
- **memories**: Extracted memories (can be session-based or persistent)
- **events**: Event logs for research data collection
- **survey_responses**: Survey response data

See `backend/app/models.py` for complete schema definitions.

## Contributing

This is a research project. For questions or contributions, please contact the research team.

## Documentation

- **[Research Readiness Checklist](RESEARCH_READINESS.md)** - Complete list of remaining tasks and open questions for research readiness

## License

Research project - Purdue University

