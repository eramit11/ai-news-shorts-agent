import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
model = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-20b:free",
)

client = OpenAI(
    api_key=key,
    base_url="https://openrouter.ai/api/v1",
    timeout=30.0,
)

print("Model:", model)
print("Starting minimal request...", flush=True)

start = time.time()

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    "Return ONLY this JSON: "
                    '{"ok":true}'
                ),
            }
        ],
        temperature=0,
        max_tokens=20,
        timeout=30.0,
    )

    elapsed = time.time() - start

    print(
        f"Response received in {elapsed:.2f} seconds",
        flush=True,
    )

    print(
        response.choices[0].message.content,
        flush=True,
    )

except Exception as exc:

    elapsed = time.time() - start

    print(
        f"FAILED after {elapsed:.2f} seconds",
        flush=True,
    )

    print(
        type(exc).__name__,
        flush=True,
    )

    print(
        str(exc),
        flush=True,
    )