import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

# Optional: force a primary model via .env (PRIMARY_MODEL=gemini-3.5-flash-lite)
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "").strip()
_FALLBACKS = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash-001"]
GEMINI_MODELS = ([PRIMARY_MODEL] + [m for m in _FALLBACKS if m != PRIMARY_MODEL]) if PRIMARY_MODEL else _FALLBACKS

MAX_AGENT_ITER = 6
HISTORY_TURNS = 12