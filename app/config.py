import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
GEMINI_MODELS = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash-001"]

MAX_AGENT_ITER = 6
HISTORY_TURNS = 12