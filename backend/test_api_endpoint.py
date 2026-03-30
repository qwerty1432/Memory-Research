"""
Quick test to check if the backend API endpoint is working
Tests both the backend server and the chat endpoint
"""
import requests
import json
import sys
from dotenv import load_dotenv

load_dotenv()

def test_backend_health():
    """Test if backend server is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running")
            return True
        else:
            print(f"⚠️  Backend responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend server is NOT running")
        print("   Start it with: cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ Error checking backend: {e}")
        return False

def test_chat_endpoint(user_id: str, session_id: str, message: str = "Hello, this is a test"):
    """Test the chat endpoint with a real request"""
    url = "http://localhost:8000/chat"
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "message": message
    }
    
    print(f"\nTesting chat endpoint...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Chat endpoint working!")
            print(f"Response: {data.get('response', 'No response')[:200]}...")
            print(f"Memory candidates: {len(data.get('memory_candidates', []))}")
            return True
        elif response.status_code == 404:
            error = response.json()
            print(f"❌ Error: {error.get('detail', 'Not found')}")
            print("   Make sure the user_id and session_id exist in the database")
            return False
        else:
            print(f"❌ Error: Status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out (API may be slow)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Backend API Test")
    print("=" * 60)
    
    # Test backend health
    if not test_backend_health():
        sys.exit(1)
    
    # Test chat endpoint if user_id and session_id provided
    if len(sys.argv) >= 3:
        user_id = sys.argv[1]
        session_id = sys.argv[2]
        message = sys.argv[3] if len(sys.argv) > 3 else "Hello, this is a test"
        test_chat_endpoint(user_id, session_id, message)
    else:
        print("\n💡 To test the chat endpoint, provide user_id and session_id:")
        print("   python test_api_endpoint.py <user_id> <session_id> [message]")
        print("\n   Get your IDs from browser console:")
        print("   localStorage.getItem('user_id')")
        print("   localStorage.getItem('session_id')")
