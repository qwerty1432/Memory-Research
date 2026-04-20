"""
Purdue GenAI API client for chat completions.

Uses sync httpx in a thread pool because httpx.AsyncClient has a known
DNS/SSL incompatibility with the anyio backend on this server (async
times out while sync completes in ~2 s).

Model: fixed to llama4:latest for this study (see get_genai_model). Not configurable via env.

Keys: set GENAI_API_KEYS=key1,key2,... or comma-separated GENAI_API_KEY.
      Keys are chosen round-robin per API call to spread rate limits.
"""
import asyncio
import os
import re
import threading
import time
import httpx
import json
from typing import Any, AsyncIterator, Optional


GENAI_API_URL = "https://genai.rcac.purdue.edu/api/chat/completions"


def _extract_assistant_content(message: Any) -> str:
    """
    Normalize assistant text from chat completion message.
    Some API responses return content as a list of parts or use alternate fields.
    """
    if not isinstance(message, dict):
        return ""
    c = message.get("content")
    if isinstance(c, str) and c.strip():
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for p in c:
            if isinstance(p, dict):
                if p.get("type") == "text" and "text" in p:
                    parts.append(str(p["text"]))
                elif "text" in p:
                    parts.append(str(p["text"]))
                elif "content" in p:
                    parts.append(str(p["content"]))
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts).strip()
    if isinstance(c, str):
        return c
    for key in ("reasoning_content", "reasoning", "text"):
        v = message.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _extract_delta_text(delta: Any) -> str:
    """Text from a streaming chunk's delta (OpenAI-compatible; some models use lists or reasoning fields)."""
    if not isinstance(delta, dict):
        return ""
    c = delta.get("content")
    if isinstance(c, str) and c:
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for p in c:
            if isinstance(p, dict):
                if p.get("type") == "text" and "text" in p:
                    parts.append(str(p["text"]))
                elif "text" in p:
                    parts.append(str(p["text"]))
                elif "content" in p:
                    parts.append(str(p["content"]))
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return ""


def sanitize_companion_public_output(text: str) -> str:
    """
    Some models emit planning plus a final 'Let's produce:' block in the same user-visible
    string. Keep only the final conversational part when those markers are present.
    """
    if not text or not text.strip():
        return text
    t = text.strip()
    # Prefer text after the last 'Let's produce:' (model sometimes echoes full plan first)
    if re.search(r"(?is)let's produce\s*:", t):
        parts = re.split(r"(?is)let's produce\s*:", t)
        if len(parts) > 1:
            tail = parts[-1].strip()
            if tail:
                return tail
    for label in ("final response:", "final answer:", "assistant response:"):
        low = t.lower()
        idx = low.rfind(label)
        if idx != -1:
            tail = t[idx + len(label) :].strip()
            if tail:
                return tail
    return t


# Single study model — all chat completions use this id with Purdue GenAI.
STUDY_GENAI_MODEL = "llama4:latest"

_keys_cache: list[str] | None = None
_key_lock = threading.Lock()
_key_rr = 0


def get_genai_model() -> str:
    """Model id for chat completions (OpenAI-compatible body). Fixed for this study."""
    return STUDY_GENAI_MODEL


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
    data = response.json()
    if "choices" not in data or not data["choices"]:
        raise Exception(f"Unexpected response format: {data}")

    msg = data["choices"][0].get("message") or {}
    text = _extract_assistant_content(msg)
    usage = data.get("usage") or {}
    comp_toks = int(usage.get("completion_tokens") or 0)

    if not text.strip() and isinstance(msg, dict):
        print(f"[GenAI] warn: empty assistant text; message keys={list(msg.keys())}")

    # The API sometimes returns message.content="" on non-stream while usage still
    # reports completion_tokens > 0. Retry as SSE aggregation when tokens were billed
    # but the JSON body has no visible text.
    if not text.strip() and comp_toks > 0:
        # Tiny max_tokens (e.g. 32) can be exhausted by internal reasoning before visible text; retry
        # stream with a floor so the model can emit assistant content.
        retry_max = max_tokens
        if retry_max is not None:
            retry_max = max(retry_max, 256)
        else:
            retry_max = 512
        print(
            "[GenAI] non-stream body empty but completion_tokens>0; aggregating stream "
            f"(max_tokens={retry_max})..."
        )
        parts: list[str] = []
        async for chunk in stream_genai(
            messages, temperature=temperature, max_tokens=retry_max
        ):
            parts.append(chunk)
        return sanitize_companion_public_output("".join(parts))

    return sanitize_companion_public_output(text)


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
        chunks: list[str] = []
        raw_lines: list[str] = []
        print(f"[GenAI] key_slot={key_slot} | stream request...")
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", GENAI_API_URL, headers=headers, json=body) as resp:
                if resp.status_code != 200:
                    error_text = resp.read()
                    raise Exception(f"GenAI API error: {resp.status_code}, {error_text.decode()}")
                for line in resp.iter_lines():
                    if not line:
                        continue
                    # SSE: "data: {...}" or "data:{...}"; some proxies omit space
                    if line.startswith("data:"):
                        data_str = line[5:].lstrip()
                    elif line.startswith("{"):
                        data_str = line
                    else:
                        continue
                    if data_str.strip() == "[DONE]":
                        break
                    if len(raw_lines) < 12:
                        raw_lines.append(data_str[:400])
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if "choices" not in data or not data["choices"]:
                        continue
                    ch0 = data["choices"][0]
                    delta = ch0.get("delta") or {}
                    piece = _extract_delta_text(delta)
                    if not piece:
                        piece = _extract_assistant_content(ch0.get("message") or {})
                    if piece:
                        chunks.append(piece)
        if not chunks and raw_lines:
            print(
                "[GenAI] warn: stream yielded no text; first chunk lines (truncated):\n  "
                + "\n  ".join(raw_lines[:5])
            )
        return chunks

    chunks = await asyncio.to_thread(_sync_stream)
    for chunk in chunks:
        yield chunk


def __getattr__(name: str):
    """Backward compatibility: legacy GENAI_MODEL import."""
    if name == "GENAI_MODEL":
        return get_genai_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
