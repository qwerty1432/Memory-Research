from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, memory_manager, prompt_builder, logging
from ..models import Message, Session as SessionModel
from ..genai_client import call_genai, stream_genai
from uuid import UUID
import os
import json
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=schemas.ChatResponse)
async def chat(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Handle chat message and return response"""
    # Verify user exists
    user = db.query(models.User).filter(models.User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get user's condition
    condition = user.condition_id
    
    # Get context based on condition
    context = memory_manager.get_context(request.user_id, request.session_id, condition, db)
    
    # Build messages for GenAI API
    messages = prompt_builder.build_messages(context, request.message)
    
    # Log message sent
    logging.log_message_sent(db, request.user_id, request.session_id, request.message)
    
    # Call GenAI API
    try:
        response_text = await call_genai(messages, stream=False)
    except Exception as e:
        # Log first attempt error
        error_msg = str(e)
        print(f"GenAI API Error (first attempt): {error_msg}")
        logging.log_error(db, "error_chat_api", request.user_id, f"First attempt: {error_msg}")
        
        # Retry once
        try:
            response_text = await call_genai(messages, stream=False)
        except Exception as retry_error:
            error_msg = str(retry_error)
            print(f"GenAI API Error (retry): {error_msg}")
            logging.log_error(db, "error_chat_api", request.user_id, f"Retry failed: {error_msg}")
            response_text = "Response unavailable. Please try again."
    
    # Save user message
    user_message = Message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    
    # Save assistant response
    assistant_message = Message(
        session_id=request.session_id,
        role="assistant",
        content=response_text
    )
    db.add(assistant_message)
    db.commit()
    
    # Log message received
    logging.log_message_received(db, request.user_id, request.session_id, response_text)
    
    # Extract memory candidates using LLM
    try:
        # Get existing memories for deduplication
        existing_memories = memory_manager.get_all_existing_memories(
            request.user_id, 
            request.session_id, 
            db
        )
        
        # Extract memories from USER MESSAGE ONLY (not assistant response)
        memory_candidates_text = await prompt_builder.extract_memories_from_conversation(
            request.message,  # Only user message, no assistant response
            existing_memories
        )
        
        # Filter out duplicates and create memory candidates
        memory_candidates = []
        for candidate_text in memory_candidates_text:
            # Check if this is a duplicate
            if not memory_manager.check_memory_duplicate(
                candidate_text,
                request.user_id,
                request.session_id,
                db
            ):
                # Not a duplicate, create the candidate
                memory = memory_manager.create_memory_candidate(
                    request.user_id,
                    request.session_id,
                    candidate_text,
                    db
                )
                memory_candidates.append(memory)
                logging.log_memory_created(db, request.user_id, memory.memory_id)
    except Exception as e:
        # Silently skip memory extraction on error
        logging.log_error(db, "error_memory_extraction", request.user_id, str(e))
        memory_candidates = []
    
    # Get all inactive memory candidates for this session
    all_candidates = memory_manager.get_memory_candidates(request.user_id, request.session_id, db)
    
    return {
        "response": response_text,
        "memory_candidates": [schemas.MemoryResponse.model_validate(m) for m in all_candidates]
    }


@router.post("/stream")
async def chat_stream(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Stream chat response using Server-Sent Events"""
    # Verify user and session
    user = db.query(models.User).filter(models.User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    session = db.query(SessionModel).filter(SessionModel.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get context and build messages
    condition = user.condition_id
    context = memory_manager.get_context(request.user_id, request.session_id, condition, db)
    messages = prompt_builder.build_messages(context, request.message)
    
    # Log message sent
    logging.log_message_sent(db, request.user_id, request.session_id, request.message)
    
    async def generate():
        try:
            response_text = ""
            # Stream response from GenAI API
            async for chunk in stream_genai(messages):
                response_text += chunk
                yield {"data": json.dumps({"token": chunk})}
            
            # Save messages to database
            user_message = Message(
                session_id=request.session_id,
                role="user",
                content=request.message
            )
            db.add(user_message)
            
            assistant_message = Message(
                session_id=request.session_id,
                role="assistant",
                content=response_text
            )
            db.add(assistant_message)
            db.commit()
            
            logging.log_message_received(db, request.user_id, request.session_id, response_text)
            
            # Extract and create memory candidates
            try:
                # Get existing memories for deduplication
                existing_memories = memory_manager.get_all_existing_memories(
                    request.user_id,
                    request.session_id,
                    db
                )
                
                # Extract memories from USER MESSAGE ONLY (not assistant response)
                memory_candidates_text = await prompt_builder.extract_memories_from_conversation(
                    request.message,  # Only user message, no assistant response
                    existing_memories
                )
                
                # Filter out duplicates and create memory candidates
                for candidate_text in memory_candidates_text:
                    # Check if this is a duplicate
                    if not memory_manager.check_memory_duplicate(
                        candidate_text,
                        request.user_id,
                        request.session_id,
                        db
                    ):
                        # Not a duplicate, create the candidate
                        memory = memory_manager.create_memory_candidate(
                            request.user_id,
                            request.session_id,
                            candidate_text,
                            db
                        )
                        logging.log_memory_created(db, request.user_id, memory.memory_id)
            except Exception as e:
                logging.log_error(db, "error_memory_extraction", request.user_id, str(e))
            
            # Send final candidates
            all_candidates = memory_manager.get_memory_candidates(request.user_id, request.session_id, db)
            yield {"data": json.dumps({"done": True, "candidates": [{"memory_id": str(m.memory_id), "text": m.text} for m in all_candidates]})}
            
        except Exception as e:
            logging.log_error(db, "error_chat_api", request.user_id, str(e))
            yield {"data": json.dumps({"error": "Response unavailable. Please try again."})}
    
    return EventSourceResponse(generate())

