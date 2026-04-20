"""Run on the server: cd ~/app/backend && ~/venv/bin/python test_genai_keys.py"""
import asyncio
import json
import os
from dotenv import load_dotenv

import httpx

load_dotenv()


async def main():
    from app.genai_client import (
        GENAI_API_URL,
        call_genai,
        configured_key_count,
        get_api_key,
        get_genai_model,
        next_api_key,
    )

    n = configured_key_count()
    print(f"Configured keys: {n}")
    print(f"Model: {get_genai_model()}")
    print("Round-robin slots (4 calls):")
    for i in range(4):
        _, slot = next_api_key()
        print(f"  call {i + 1} -> key_slot={slot}")
    # Tiny live call to RCAC (uses next key in sequence)
    print("Live ping (1 GenAI call)...")
    # Some models may use the whole small budget before visible assistant text;
    # use enough headroom for a one-word reply after internal reasoning.
    out = await call_genai(
        [{"role": "user", "content": "Reply with exactly one word: ok"}],
        stream=False,
        max_tokens=256,
    )
    print(f"  Response (repr): {repr((out or '')[:120])}")
    if not (out or "").strip():
        print("  DEBUG: empty text — dumping first 2500 chars of raw JSON:")
        key = get_api_key()
        body = {
            "model": get_genai_model(),
            "messages": [{"role": "user", "content": "Say hi in one word."}],
            "stream": False,
            "max_tokens": 256,
            "temperature": 0.7,
        }
        r = httpx.post(
            GENAI_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body,
            timeout=60.0,
        )
        print(json.dumps(r.json(), indent=2)[:2500])


if __name__ == "__main__":
    asyncio.run(main())
