"""Run on the server: cd ~/app/backend && ~/venv/bin/python test_genai_keys.py"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def main():
    from app.genai_client import (
        configured_key_count,
        get_genai_model,
        next_api_key,
        call_genai,
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
    out = await call_genai(
        [{"role": "user", "content": "Reply with only: ok"}],
        stream=False,
        max_tokens=5,
    )
    print(f"  Response: {(out or '')[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
