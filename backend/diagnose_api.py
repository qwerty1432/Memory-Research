"""
Diagnostic script to check API connectivity and configuration
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def diagnose():
    """Diagnose API issues"""
    print("=" * 60)
    print("GenAI API Diagnostic")
    print("=" * 60)
    
    # Check if we can import the client (loads keys from GENAI_API_KEY / GENAI_API_KEYS)
    try:
        from app.genai_client import (
            call_genai,
            GENAI_API_URL,
            get_genai_model,
            get_api_key,
            configured_key_count,
        )
        print(f"✅ GenAI client imported successfully")
        print(f"   URL: {GENAI_API_URL}")
        print(f"   Model: {get_genai_model()}")
        print(f"   API keys configured: {configured_key_count()}")
        api_key = get_api_key()
        print(f"   First key prefix: {api_key[:20]}...")
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        print("   Set GENAI_API_KEY=sk-... or GENAI_API_KEYS=key1,key2,...")
        return False
    except Exception as e:
        print(f"❌ ERROR importing genai_client: {e}")
        return False

    # Test API call
    print("\nTesting API call...")
    messages = [
        {"role": "system", "content": "You are a friendly AI companion."},
        {"role": "user", "content": "Hello, say 'test successful' if you can hear me."}
    ]
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": get_genai_model(),
                "messages": messages,
                "stream": False,
                "temperature": 0.7
            }
            
            print(f"   Sending request to {GENAI_API_URL}...")
            response = await client.post(GENAI_API_URL, headers=headers, json=body)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    print(f"✅ API call successful!")
                    print(f"   Response: {content[:100]}...")
                    return True
                else:
                    print(f"❌ Unexpected response format: {data}")
                    return False
            elif response.status_code == 401:
                print(f"❌ ERROR: Unauthorized (401)")
                print(f"   Your API key may be invalid or expired")
                print(f"   Response: {response.text[:200]}")
                return False
            else:
                print(f"❌ ERROR: API returned status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
    except httpx.TimeoutException:
        print(f"❌ ERROR: Request timed out")
        print(f"   The API may be slow or unreachable")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(diagnose())
    sys.exit(0 if result else 1)
