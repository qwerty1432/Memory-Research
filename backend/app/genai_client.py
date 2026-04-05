"""
Purdue GenAI API client for chat completions.

Uses sync httpx in a thread pool because httpx.AsyncClient has a known
DNS/SSL incompatibility with the anyio backend on this server (async
times out while sync completes in ~2 s).

Model: set GENAI_MODEL (default gpt-oss:latest — RCAC keeps this hot in GPU memory).

Keys: set GENAI_API_KEYS=key1,key2,... or comma-separated GENAI_API_KEY.
      Keys are chosen round-robin per API call to spread rate limits.
"""
import asyncio
import os
import threading
import time
import httpx
import json
from typing import AsyncIterator, Optional


GENAI_API_URL = "https://genai.rcac.purdue.edu/api/chat/completions"

# Default: RCAC indicated gpt-oss:latest / llama4 stay resident; older models may cold-load.
_DEFAULT_MODEL = "gpt-oss:latest"

_keys_cache: list[str] | None = None
_key_lock = threading.Lock()
_key_rr = 0


def get_genai_model() -> str:
    """Model id for chat completions (OpenAI-compatible body)."""
    return (os.getenv("GENAI_MODEL") or _DEFAULT_MODEL).strip()


def _load_api_keys() -> list[str]:
    global _keys_cache
    if _keys_cache is not None:
        return _keys_cache
    raw = (os.getenv("GENAI_API_KEYS") or "").strip()
    if raw:
        _keys_cache = [k.strip() for k in raw.split(",") if k.strip()]
    else:
        single = (os.getenv("GENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        if "," in single:
            _keys_cache = [k.strip() for k in single.split(",") if k.strip()]
        elif single:
            _keys_cache = [single]
        else:
            _keys_cache = []
    if not _keys_cache:
        raise ValueError(
            "No GenAI API keys found. Set GENAI_API_KEYS or GENAI_API_KEY (comma-separated for multiple keys)."
        )
    return _keys_cache


def next_api_key() -> tuple[str, int]:
    """Round-robin (api_key, key_slot). key_slot is 0..n-1 for logs (no secrets)."""
    keys = _load_api_keys()
    if len(keys) == 1:
        return keys[0], 0
    global _key_rr
    with _key_lock:
        slot = _key_rr % len(keys)
        k = keys[slot]
        _key_rr += 1
        return k, slot


def get_api_key() -> str:
    """Return one key (first in list). Prefer next_api_key() for new calls."""
    return _load_api_keys()[0]


def configured_key_count() -> int:
    """Number of API keys configured (for logging / diagnostics)."""
    return len(_load_api_keys())


def _sync_call(headers: dict, body: dict, key_slot: int = -1) -> httpx.Response:
    t0 = time.time()
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(GENAI_API_URL, headers=headers, json=body)
    elapsed = time.time() - t0
    tokens = resp.json().get("usage", {}) if resp.status_code == 200 else {}
    slot_part = f"key_slot={key_slot} | " if key_slot >= 0 else ""
    print(f"[GenAI] {slot_part}{elapsed:.1f}s | status={resp.status_code} | "
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
    api_key, key_slot = next_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": get_genai_model(),
        "messages": messages,
        "stream": stream,
        "temperature": temperature
    }

    if max_tokens:
        body["max_tokens"] = max_tokens

    response = await asyncio.to_thread(_sync_call, headers, body, key_slot)

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
    api_key, key_slot = next_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": get_genai_model(),
        "messages": messages,
        "stream": True,
        "temperature": temperature
    }

    if max_tokens:
        body["max_tokens"] = max_tokens

    def _sync_stream():
        chunks = []
        print(f"[GenAI] key_slot={key_slot} | stream request...")
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


def __getattr__(name: str):
    """Backward compatibility: GENAI_MODEL -> get_genai_model()."""
    if name == "GENAI_MODEL":
        return get_genai_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
