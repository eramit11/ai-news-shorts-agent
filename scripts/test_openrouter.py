import os
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
key = os.getenv("OPENROUTER_API_KEY")
model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
print("Provider:", os.getenv("AI_PROVIDER"))
print("Model:", model)
print("Key loaded:", bool(key))
if not key:
    raise SystemExit("OPENROUTER_API_KEY is missing.")
client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1", default_headers={"HTTP-Referer": "https://github.com/ai-news-shorts-agent", "X-Title": "AI News Shorts Agent"})
response = client.chat.completions.create(model=model, messages=[{"role":"user", "content":"Reply with exactly: OpenRouter test OK"}], temperature=0)
print("Response:", response.choices[0].message.content)
