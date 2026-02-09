"""
Quick test script for GenAI API
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_genai():
    """Test the GenAI API directly"""
    from app.genai_client import call_genai
    
    messages = [
        {"role": "system", "content": "You are a friendly AI companion."},
        {"role": "user", "content": "Hello, my name is Kabeer. What is your name?"}
    ]
    
    try:
        print("Testing GenAI API...")
        print(f"API Key: {os.getenv('GENAI_API_KEY', 'NOT FOUND')[:20]}...")
        response = await call_genai(messages, stream=False)
        print(f"\n✅ Success! Response: {response}")
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_genai())


