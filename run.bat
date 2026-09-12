@echo off
REM Start Sevana Voice civic agent
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
if not exist .env (
  echo Please copy .env.example to .env and add your GROQ_API_KEY
)
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload