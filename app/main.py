import os
from fastapi import FastAPI, File, HTTPException, UploadFile, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, asr, db, tts

_BASE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_BASE, "..", "static")
TTS_DIR = os.path.join(STATIC_DIR, "tts")

app = FastAPI(title="Sevana Voice — Kerala Civic Agent")


class ChatRequest(BaseModel):
    text: str
    lang: str = "ml"


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str


class ChatResponse(BaseModel):
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


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.webmanifest"), media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")


def _current_user(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    user = db.get_user_for_token(token) if scheme.lower() == "bearer" and token else None
    if not user:
        raise HTTPException(401, "Please sign in to access your private assistant.")
    return user


@app.post("/api/auth/register", response_model=AuthResponse)
def register(req: AuthRequest):
    try:
        user = db.create_user(req.email, req.password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return AuthResponse(token=db.issue_token(user["id"]), email=user["email"])


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: AuthRequest):
    user = db.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(401, "Incorrect email or password.")
    return AuthResponse(token=db.issue_token(user["id"]), email=user["email"])


@app.post("/api/auth/logout")
def logout(authorization: str = Header(default="")):
    _, _, token = authorization.partition(" ")
    if token:
        db.revoke_token(token)
    return {"ok": True}


@app.get("/api/me")
def me(authorization: str = Header(default="")):
    return _current_user(authorization)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, authorization: str = Header(default="")):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    user = _current_user(authorization)
    reply = await _run_agent(user["id"], text, req.lang)
    audio_url = ""
    try:
        audio_path = await tts.synthesize(reply, req.lang)
        audio_url = f"/static/tts/{os.path.basename(audio_path)}"
    except tts.TTSUnavailable:
        pass
    return ChatResponse(user_text=text, reply=reply, audio_url=audio_url)


@app.get("/api/applications")
def applications(authorization: str = Header(default="")):
    user = _current_user(authorization)
    return {"applications": db.list_applications(user["id"])}


async def _run_agent(sid: str, text: str, lang: str = "ml") -> str:
    import asyncio

    return await asyncio.to_thread(agent.run_turn, sid, text, lang)


@app.post("/api/asr")
async def asr_upload(file: UploadFile = File(...), authorization: str = Header(default="")):
    _current_user(authorization)
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
async def tts_endpoint(text: str = "ഹലോ", lang: str = "ml"):
    try:
        path = await tts.synthesize(text, lang)
    except tts.TTSUnavailable as e:
        raise HTTPException(502, str(e))
    return FileResponse(path, media_type="audio/mpeg")
