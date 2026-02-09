"""
Purdue GenAI API client for chat completions
"""
import os
import httpx
import json
from typing import AsyncIterator, Optional


GENAI_API_URL = "https://genai.rcac.purdue.edu/api/chat/completions"
GENAI_MODEL = "llama3.1:latest"


def get_api_key() -> str:
    """Get the GenAI API key from environment"""
    api_key = os.getenv("GENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("GENAI_API_KEY or OPENAI_API_KEY not found in environment variables")
    return api_key


async def call_genai(
    messages: list[dict],
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> str:
    """
    Call Purdue GenAI API for chat completion.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        stream: Whether to stream the response
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
    
    Returns:
        Full response text (for non-streaming) or empty string (for streaming)
    """
    api_key = get_api_key()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    body = {
        "model": GENAI_MODEL,
        "messages": messages,
        "stream": stream,
        "temperature": temperature
    }
    
    if max_tokens:
        body["max_tokens"] = max_tokens
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(GENAI_API_URL, headers=headers, json=body)
        
        if response.status_code != 200:
            raise Exception(f"GenAI API error: {response.status_code}, {response.text}")
        
        if stream:
            # For streaming, return empty string (handled separately)
            return ""
        else:
            # Parse non-streaming response
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"Unexpected response format: {data}")


async def stream_genai(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> AsyncIterator[str]:
    """
    Stream responses from Purdue GenAI API.
    
    Yields:
        Chunks of text as they arrive
    """
    api_key = get_api_key()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    body = {
        "model": GENAI_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": temperature
    }
    
    if max_tokens:
        body["max_tokens"] = max_tokens
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", GENAI_API_URL, headers=headers, json=body) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise Exception(f"GenAI API error: {response.status_code}, {error_text.decode()}")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue


