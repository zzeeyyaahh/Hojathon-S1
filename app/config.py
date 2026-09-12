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

# Sign-up / profile setup: these fields make the agent actually KNOW the citizen
PROFILE_FIELDS = [
    {"field": "name", "label_ml": "നിങ്ങളുടെ പേര് എന്താണ്?", "label_en": "What is your name?"},
    {"field": "age", "label_ml": "നിങ്ങളുടെ വയസ്സ് എത്രയാണ്?", "label_en": "How old are you?"},
    {"field": "family_size", "label_ml": "കുടുംബത്തിലെ അംഗങ്ങളുടെ എണ്ണം എത്ര?", "label_en": "How many people in your family?"},
    {"field": "annual_income", "label_ml": "കുടുംബത്തിന്റെ വാർഷിക വരുമാനം എത്രയാണ് (രൂപയിൽ)?", "label_en": "What is the annual family income (in rupees)?"},
    {"field": "district", "label_ml": "ഏത് ജില്ലയിലാണ് നിങ്ങൾ താമസിക്കുന്നത്?", "label_en": "Which district do you live in?"},
    {"field": "occupation", "label_ml": "നിങ്ങളുടെ തൊഴിൽ എന്താണ്?", "label_en": "What is your occupation?"},
]

MAX_AGENT_ITER = 6
HISTORY_TURNS = 12