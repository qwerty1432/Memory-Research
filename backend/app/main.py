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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URL
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

