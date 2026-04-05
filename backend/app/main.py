from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, engine
from . import models
from .routers import auth, chat, memory, condition, session, survey
import os

# Initialize database
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Companion Research Platform API",
    description="Backend API for studying AI memory persistence and user control",
    version="1.0.0"
)

# CORS middleware
# Allow Qualtrics domains and tunneling services for iframe embedding
import os
environment = os.getenv("ENVIRONMENT", "development")

# Base allowed origins
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# In development, allow all origins for testing with ngrok and other tunneling services
# In production, you should specify exact Qualtrics survey URLs
if environment == "development":
    # Allow all origins in development (for testing with ngrok, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://.*",  # Allow all HTTP/HTTPS origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # In production, add specific Qualtrics survey URLs
    # You can add them via environment variable ALLOWED_ORIGINS (comma-separated)
    production_origins = allowed_origins.copy()
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
    if allowed_origins_env:
        production_origins.extend([origin.strip() for origin in allowed_origins_env.split(",")])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=production_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(condition.router)
app.include_router(session.router)
app.include_router(survey.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

    # Warm up the GenAI model so the first user request isn't slow
    import asyncio
    async def _warmup():
        try:
            from .genai_client import call_genai
            await call_genai(
                [{"role": "user", "content": "Hi"}],
                stream=False,
                max_tokens=64,
            )
            print("GenAI warm-up: OK")
        except Exception as e:
            print(f"GenAI warm-up: failed ({e}) — first request may be slow")
    asyncio.create_task(_warmup())


@app.get("/")
def root():
    return {
        "message": "AI Companion Research Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}

