import httpx
import time

print("Starting httpx test...")
start = time.time()
try:
    r = httpx.post(
        "https://genai.rcac.purdue.edu/api/chat/completions",
        headers={
            "Authorization": "Bearer sk-8b67b7413724483681f5f4360723403f",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama3.1:latest",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10,
        },
        timeout=30.0,
    )
    print(f"Done: {r.status_code} in {time.time()-start:.1f}s")
    print(r.text[:200])
except Exception as e:
    print(f"Error after {time.time()-start:.1f}s: {e}")
