"""
Purdue GenAI API client for chat completions.

Uses sync httpx in a thread pool because httpx.AsyncClient has a known
DNS/SSL incompatibility with the anyio backend on this server (async
times out while sync completes in ~2 s).
"""
import asyncio
import os
import time
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


def _sync_call(headers: dict, body: dict) -> httpx.Response:
    t0 = time.time()
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(GENAI_API_URL, headers=headers, json=body)
    elapsed = time.time() - t0
    tokens = resp.json().get("usage", {}) if resp.status_code == 200 else {}
    print(f"[GenAI] {elapsed:.1f}s | status={resp.status_code} | "
          f"max_tokens={body.get('max_tokens','none')} | "
          f"prompt_tok={tokens.get('prompt_tokens','?')} "
          f"comp_tok={tokens.get('completion_tokens','?')}")
    return resp


async def call_genai(
    messages: list[dict],
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> str:
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

    response = await asyncio.to_thread(_sync_call, headers, body)

    if response.status_code != 200:
        raise Exception(f"GenAI API error: {response.status_code}, {response.text}")

    if stream:
        return ""
    else:
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
    Uses sync httpx in a background thread, then yields chunks.
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

    def _sync_stream():
        chunks = []
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", GENAI_API_URL, headers=headers, json=body) as resp:
                if resp.status_code != 200:
                    error_text = resp.read()
                    raise Exception(f"GenAI API error: {resp.status_code}, {error_text.decode()}")
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    chunks.append(content)
                        except json.JSONDecodeError:
                            continue
        return chunks

    chunks = await asyncio.to_thread(_sync_stream)
    for chunk in chunks:
        yield chunk
