import os
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, asr, db, tts

_BASE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_BASE, "..", "static")
TTS_DIR = os.path.join(STATIC_DIR, "tts")

app = FastAPI(title="Sevana Voice — Kerala Civic Agent")


class ChatRequest(BaseModel):
    session_id: str = ""
    text: str


class SessionResponse(BaseModel):
    session_id: str


class ChatResponse(BaseModel):
    session_id: str
    user_text: str
    reply: str
    audio_url: str = ""


@app.on_event("startup")
def _startup():
    db.init_db()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.post("/api/session", response_model=SessionResponse)
def create_session():
    return SessionResponse(session_id=uuid.uuid4().hex[:16])


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    sid = req.session_id or "demo"
    reply = await _run_agent(sid, text)
    audio_path = await tts.synthesize(reply)
    audio_url = f"/static/tts/{os.path.basename(audio_path)}"
    return ChatResponse(session_id=sid, user_text=text, reply=reply, audio_url=audio_url)


async def _run_agent(sid: str, text: str) -> str:
    import asyncio

    return await asyncio.to_thread(agent.run_turn, sid, text)


@app.post("/api/asr")
async def asr_upload(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(400, "empty audio")
    try:
        text = await _run_asr(content, file.filename or "audio.webm", file.content_type or "audio/webm")
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {e}")
    return {"text": text}


async def _run_asr(content, filename, mime):
    import asyncio

    return await asyncio.to_thread(asr.transcribe, content, filename, mime)


@app.get("/api/tts")
async def tts_endpoint(text: str = "ഹലോ"):
    path = await tts.synthesize(text)
    return FileResponse(path, media_type="audio/mpeg")