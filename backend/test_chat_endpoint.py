"""
Test the chat endpoint directly
Usage: python test_chat_endpoint.py <user_id> <session_id>
"""
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

async def test_chat(user_id: str, session_id: str, message: str = "Hello, my name is Kabeer"):
    """Test the chat endpoint"""
    from app.database import SessionLocal
    from app.routers.chat import chat
    from app.schemas import ChatRequest
    from uuid import UUID
    
    db = SessionLocal()
    try:
        request = ChatRequest(
            user_id=UUID(user_id),
            session_id=UUID(session_id),
            message=message
        )
        
        print(f"Testing chat endpoint...")
        print(f"User ID: {user_id}")
        print(f"Session ID: {session_id}")
        print(f"Message: {message}\n")
        
        result = await chat(request, db)
        print(f"✅ Success!")
        print(f"Response: {result['response']}")
        print(f"Memory candidates: {len(result['memory_candidates'])}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_chat_endpoint.py <user_id> <session_id> [message]")
        print("\nTo get your IDs, run in browser console:")
        print("  localStorage.getItem('user_id')")
        print("  localStorage.getItem('session_id')")
        sys.exit(1)
    
    user_id = sys.argv[1]
    session_id = sys.argv[2]
    message = sys.argv[3] if len(sys.argv) > 3 else "Hello, my name is Kabeer"
    
    asyncio.run(test_chat(user_id, session_id, message))


