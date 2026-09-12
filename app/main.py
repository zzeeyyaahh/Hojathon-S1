import base64
import json
import os
from fastapi import FastAPI, File, HTTPException, UploadFile, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import agent, asr, browser, db, kb, tts

_BASE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_BASE, "..", "static")
TTS_DIR = os.path.join(STATIC_DIR, "tts")

app = FastAPI(title="Sevana Voice — Kerala Civic Agent")
# Ensure one-off workers and test clients get the same schema as the web server.
db.init_db()


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


class WorkflowStartRequest(BaseModel):
    service_id: str


class WorkflowFieldsRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class BrowserOpenRequest(BaseModel):
    url: str


def _service_or_404(service_id: str) -> dict:
    service = kb.get_service(service_id)
    if not service:
        raise HTTPException(404, "Unknown service.")
    return service


def _workflow_view(draft: dict, service: dict) -> dict:
    payload = draft["payload"]
    fields = service.get("form_fields", [])
    missing = [field for field in fields if not str(payload.get(field["field"], "")).strip()]
    return {
        "id": draft["id"], "service": {key: service.get(key) for key in ("id", "name_en", "name_ml", "portal", "documents_en", "documents")},
        "status": draft["status"], "values": payload,
        "fields": fields,
        "next_field": missing[0] if missing else None,
        "ready_for_review": not missing,
        "reviewed_at": draft["reviewed_at"],
    }


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


@app.post("/api/workflows/start")
def start_workflow(req: WorkflowStartRequest, authorization: str = Header(default="")):
    """Create a service-specific draft and prefill only facts the user saved earlier."""
    user = _current_user(authorization)
    service = _service_or_404(req.service_id)
    profile = db.get_profile(user["id"])
    aliases = {"applicant_name": "name"}
    values = {}
    for field in service.get("form_fields", []):
        name = field["field"]
        remembered = profile.get(name) or profile.get(aliases.get(name, ""))
        if remembered:
            values[name] = remembered
    return _workflow_view(db.create_draft(user["id"], service["id"], values), service)


@app.get("/api/workflows/{draft_id}")
def get_workflow(draft_id: str, authorization: str = Header(default="")):
    user = _current_user(authorization)
    draft = db.get_draft(draft_id, user["id"])
    if not draft:
        raise HTTPException(404, "Draft not found.")
    return _workflow_view(draft, _service_or_404(draft["service_id"]))


@app.put("/api/workflows/{draft_id}/fields")
def save_workflow_fields(draft_id: str, req: WorkflowFieldsRequest, authorization: str = Header(default="")):
    user = _current_user(authorization)
    draft = db.get_draft(draft_id, user["id"])
    if not draft or draft["status"] != "collecting":
        raise HTTPException(409, "This draft cannot be edited.")
    service = _service_or_404(draft["service_id"])
    allowed = {field["field"] for field in service.get("form_fields", [])}
    updates = {key: str(value).strip() for key, value in req.values.items() if key in allowed and str(value).strip()}
    payload = {**draft["payload"], **updates}
    # The citizen asked for remembered answers. Never store portal passwords, OTPs, or CAPTCHA data.
    for key, value in updates.items():
        db.set_profile(user["id"], key, value)
    saved = db.update_draft(draft_id, user["id"], payload)
    return _workflow_view(saved, service)


@app.post("/api/workflows/{draft_id}/review")
def review_workflow(draft_id: str, authorization: str = Header(default="")):
    user = _current_user(authorization)
    draft = db.get_draft(draft_id, user["id"])
    if not draft:
        raise HTTPException(404, "Draft not found.")
    service = _service_or_404(draft["service_id"])
    view = _workflow_view(draft, service)
    if not view["ready_for_review"]:
        raise HTTPException(400, "Complete all required fields before review.")
    if draft["payload"].get("registered_mobile") != "yes":
        raise HTTPException(400, "UIDAI online updates require an Aadhaar-linked mobile number for OTP. Please use an Aadhaar Enrolment Centre.")
    reviewed = db.update_draft(draft_id, user["id"], draft["payload"], status="reviewed", reviewed=True)
    return _workflow_view(reviewed, service)


@app.post("/api/workflows/{draft_id}/submit")
async def submit_workflow(draft_id: str, authorization: str = Header(default="")):
    user = _current_user(authorization)
    draft = db.get_draft(draft_id, user["id"])
    if not draft or draft["status"] != "reviewed":
        raise HTTPException(409, "Review the completed form before submitting.")
    service = _service_or_404(draft["service_id"])
    receipt = db.create_application(user["id"], service["id"], draft["payload"], status="Submitted for portal run")
    db.update_draft(draft_id, user["id"], draft["payload"], status="submitted")
    # The citizen approved the reviewed draft: hand it to the agent so IT opens the
    # official portal and does the work, asking consent and pausing for OTP/CAPTCHA.
    instruction = (
        f"I reviewed and approved my {service['name_en']} request. "
        f"Confirmed details: {json.dumps(draft['payload'], ensure_ascii=False)}. "
        f"Open the official portal {service.get('portal')} in the browser window and carry out the "
        f"{service['name_en']} flow for me step by step. Fill the form with my confirmed details, "
        f"read each page before acting, and ask my permission before entering personal details or "
        f"submitting. If an OTP, CAPTCHA or login appears, stop and tell me to complete it in the window."
    )
    agent_reply = ""
    try:
        agent_reply = await _run_agent(user["id"], instruction, "en")
    except Exception as exc:  # keep the receipt even if the portal step fails
        agent_reply = f"I saved your approved {service['name_en']} request, but the portal step failed: {exc}"
    return {
        "submitted": True,
        "receipt": receipt,
        "portal": service.get("portal"),
        "message": "Approved. The agent is doing the rest of the work on the official portal now.",
        "agent_reply": agent_reply,
    }


async def _run_agent(sid: str, text: str, lang: str = "ml") -> str:
    import asyncio

    return await asyncio.to_thread(agent.run_turn, sid, text, lang)


@app.post("/api/browser/open")
def browser_open(req: BrowserOpenRequest, authorization: str = Header(default="")):
    """Open a portal in the visible browser window (e.g. a quick 'open site' button)."""
    _current_user(authorization)
    return browser.browser.open(req.url)


@app.get("/api/browser/view")
def browser_view(authorization: str = Header(default="")):
    """Live view of the shared portal window: URL, titles, loading, needs_user, and a screenshot."""
    _current_user(authorization)
    status = browser.browser.status()
    if status["active"]:
        png = browser.browser.screenshot()
        if png:
            status["screenshot"] = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    return status


@app.post("/api/browser/close")
def browser_close(authorization: str = Header(default="")):
    _current_user(authorization)
    browser.browser.close()
    return {"closed": True}


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
