# AI Companion Research Platform

A web-based chatbot designed to study how AI memory persistence and user control affect user interaction and perception. The current study runs with three research conditions covering session-only memory, persistent automatic memory, and persistent user-controlled memory.

## Architecture

- **Frontend**: Next.js + React + TypeScript + TailwindCSS
- **Backend**: FastAPI (Python 3.9+)
- **Database**: PostgreSQL (production) or SQLite (local development)
- **LLM**: Purdue GenAI API (`llama4:latest`, configured in `backend/app/genai_client.py`)

## Experimental Conditions

The platform currently uses three experimental conditions:

1. **SESSION_AUTO** (Session + Automatic): Memory lasts only for one chat session, automatically extracted
2. **PERSISTENT_AUTO** (Persistent + Automatic): All memories automatically stored and persist across sessions
3. **PERSISTENT_USER** (Persistent + User-Controlled): User approves which memories persist across sessions

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
- ✅ **Experimental Conditions**: Three research conditions aligned with the live study flow
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
| `CHAT_TONE` | Chat tone/persona: `extroverted` or `neutral` | No | `extroverted` |
| `EFFORT_CHECK_ENABLED` | Enable effort/relevance checks that may trigger follow-up questions | No | `true` |
| `EFFORT_MIN_WORDS` | Minimum words before we consider a reply “too short” (heuristic) | No | `6` |

**Example `.env` file:**
```bash
DATABASE_URL=sqlite:///./memory_research.db
GENAI_API_KEY=sk-your-api-key-here
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
CHAT_TONE=extroverted
EFFORT_CHECK_ENABLED=true
EFFORT_MIN_WORDS=6
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

## Qualtrics Integration

The chatbot can be embedded in Qualtrics surveys as an iframe. Participants are automatically authenticated using their Qualtrics Response ID (no login required).

### Local Testing with Tunneling

For local testing before deployment, use a tunneling service (e.g., ngrok) to expose your **frontend** to the internet. The Next.js app proxies API requests to your local backend via `/api/*`, so you typically only need **one tunnel** (frontend).

1. **Install ngrok**: Download from https://ngrok.com/download

2. **Start your services**:
   ```bash
   # Terminal 1: Backend
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

3. **Create a tunnel (frontend)**:
   ```bash
   ngrok http 3000
   # Note the HTTPS URL (e.g., https://xyz789.ngrok-free.dev)
   ```

4. **Test the integration**:
   - Access frontend via ngrok URL: `https://your-frontend-ngrok-url.ngrok-free.dev`
   - Test with mock Qualtrics parameters (preferred): `?response_id=test123&return_url=https://example.com`
   - (Legacy param still supported): `?qualtrics_id=test123&return_url=https://example.com`
   - Verify automatic authentication works (no login screen)
   - Test "Finish Conversation" button

### Qualtrics Survey Configuration

Add this HTML/JavaScript to your Qualtrics survey:

```html
<div id="chatbot-container" style="width: 100%; height: 80vh; min-height: 600px;">
  <iframe 
    id="chatbot-iframe"
    src="https://your-domain.com/?response_id=${e://Field/ResponseID}&return_url=${e://Field/ReturnURL}"
    style="width: 100%; height: 100%; border: none;"
    allow="microphone; camera"
  ></iframe>
</div>

<script>
  window.addEventListener('message', function(event) {
    // Verify origin for security (update with your domain)
    if (event.origin !== 'https://your-domain.com') {
      return;
    }
    
    if (event.data.action === 'finish') {
      // Mark chatbot as completed
      Qualtrics.SurveyEngine.setEmbeddedData('chatbot_completed', 'true');
      Qualtrics.SurveyEngine.setEmbeddedData('chatbot_qualtrics_id', event.data.qualtrics_id);
      
      // Advance to next survey block
      this.clickNextButton();
    }
  });
</script>
```

**Replace `https://your-domain.com` with your actual chatbot URL** (ngrok URL for testing, production URL for deployment).

### How It Works

1. **Automatic Authentication**: When a participant accesses the chatbot via Qualtrics iframe, the `response_id` parameter (Qualtrics ResponseID) is used to automatically create or authenticate the user (no password required).
   - Preferred param name: `response_id` (Qualtrics ResponseID)
   - Legacy param name still accepted: `qualtrics_id`

2. **Condition Assignment**: Experimental conditions are assigned using round-robin rotation for balanced distribution.

3. **Session Management**: Each Qualtrics interaction creates a new session, allowing tracking of multiple interactions if participants return to the chatbot.

4. **Finish Conversation**: Participants click "Finish Conversation" when done, which sends a message to the Qualtrics parent window to advance to the next survey block.

5. **Research Logging**: Key study signals are logged in the `events` table (e.g., `qualtrics_authenticated`, `effort_check`, message sent/received).

### Participant UX Notes (Study)

- **Avatar customization**: Participants can open `Menu → Avatar` to set the AI’s display name, icon color, and symbol. This changes the icon shown next to **assistant** messages.
- **Extroverted tone**: Controlled via backend env var `CHAT_TONE`.
- **Effort/relevance checks**: Controlled via backend env vars `EFFORT_CHECK_ENABLED` and `EFFORT_MIN_WORDS`. When enabled, the bot may ask a brief follow-up question if the response is too short/off-topic.
- **Bot-checking**: Deferred (out of scope for the first deployed version).

### Production Deployment

For production deployment:

1. Deploy backend and frontend to a server with HTTPS
2. Update CORS configuration in `backend/app/main.py` to include specific Qualtrics survey URLs
3. Update `frontend/.env.local` with production backend URL
4. Update Qualtrics embed code with production frontend URL
5. Test with actual Qualtrics survey in test mode before going live

## License

Research project - Purdue University

