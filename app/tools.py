import inspect
import json

from . import browser, config, db, kb

_WIZARDS: dict = {}
_PROFILE_WIZARDS: dict = {}

FUNCTION_SCHEMAS: list = []


def _register(**t):
    FUNCTION_SCHEMAS.append({"type": "function", "function": t})


def _norm_answers(raw) -> dict:
    if isinstance(raw, dict):
        if "answers" in raw and isinstance(raw["answers"], dict):
            return {k: v for k, v in raw["answers"].items()}
        return {k: v for k, v in raw.items() if k not in ("answers",)}
    if isinstance(raw, str):
        return {"answer": raw}
    return {}


def _flatten(service, answers):
    flat = _norm_answers(answers)
    for k, v in list(flat.items()):
        if isinstance(v, list):
            flat[k] = ", ".join(str(x) for x in v)
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                flat[f"{k}.{k2}"] = v2
            flat.pop(k)
    return flat


# ---------------- Tool implementations ----------------

def search_service(query: str, ctx) -> dict:
    results = kb.search_services(query or "")
    if not results:
        names = [s["name_ml"] for s in kb.get_all_services()]
        return {"found": False, "available_services_ml": names}
    return {"found": True, "service": kb.summarize_service(results[0])}


def list_services(_args, ctx) -> dict:
    return {"services": [
        {"id": s["id"], "name_ml": s["name_ml"], "name_en": s["name_en"]}
        for s in kb.get_all_services()
    ]}


def check_eligibility(service_id: str, answers, ctx) -> dict:
    service = kb.get_service(service_id or "")
    if not service:
        return {"error": f"unknown service_id: {service_id}"}
    return kb.check_eligibility(service, _flatten(service, answers))


def run_form_wizard(service_id: str, answers, ctx) -> dict:
    sid = ctx["session_id"]
    state = _WIZARDS.get(sid)
    if not state or state["service_id"] != service_id:
        state = {"service_id": service_id, "collected": {}, "waiting": None}
        _WIZARDS[sid] = state

    collected = state["collected"]
    flat = _flatten({}, answers)

    fields = kb.get_service(service_id).get("form_fields", []) if kb.get_service(service_id) else []
    pending = {f["field"] for f in fields if not collected.get(f["field"])}
    known = {f["field"] for f in fields}

    # If the caller gave no recognized field value (e.g. bare text), attach it to
    # the field we last asked for — this keeps the wizard moving even when the
    # LLM forgets to include the field key.
    if flat:
        gave_known = {k: v for k, v in flat.items() if k in known}
        if gave_known:
            collected.update(gave_known)
        else:
            raw = flat.get("answer") or next(iter(flat.values()), None)
            target = state.get("waiting") or (missing[0]["field"] if (missing := [f for f in fields if not collected.get(f["field"])]) else None)
            if raw is not None and str(raw).strip() and target:
                collected[target] = str(raw).strip()

    service = kb.get_service(service_id)
    if not service:
        return {"error": f"unknown service_id: {service_id}"}

    missing = [f for f in fields if not collected.get(f["field"])]
    filled = [f for f in fields if collected.get(f["field"])]
    progress = {
        "service_name_ml": service.get("name_ml"),
        "filled": len(filled),
        "total": len(fields),
        "current_field": None,
        "current_field_label_ml": None,
        "current_field_label_en": None,
        "collected": {f["field"]: collected[f["field"]] for f in filled},
    }
    if missing:
        nxt = missing[0]
        state["waiting"] = nxt["field"]
        progress["current_field"] = nxt["field"]
        progress["current_field_label_ml"] = nxt.get("label_ml")
        progress["current_field_label_en"] = nxt.get("label_en")
        progress["done"] = False
        return progress

    state["waiting"] = None
    progress["done"] = True
    progress["payload"] = {f["field"]: collected.get(f["field"]) for f in fields}
    progress["next_steps_ml"] = service.get("steps", [])
    progress["portal"] = service.get("portal")
    return progress


def answer_waiting_field(session_id: str, text: str) -> str | None:
    """Server-side autofill: record the user's reply as the answer to a form field.
    Returns the field name it filled, or None."""
    state = _WIZARDS.get(session_id)
    if not state or not state.get("waiting"):
        return None
    text = (text or "").strip()
    if not text or len(text) > 200:
        return None

    fields = kb.get_service(state["service_id"]).get("form_fields", []) if kb.get_service(state["service_id"]) else []
    waiting = state["waiting"]
    pending = [f for f in fields if not state["collected"].get(f["field"])]
    target = waiting

    flat = text.replace(" ", "").replace("-", "").replace(".", "")
    if flat.isdigit():
        if len(flat) == 12 and any(f["field"] == "aadhaar" for f in pending):
            target = "aadhaar"
        elif len(flat) == 10 and any(f["field"] == "phone" for f in pending):
            target = "phone"
        elif any(f["field"] == waiting and f.get("type") == "number" for f in fields):
            target = waiting
        elif any(f.get("type") == "number" for f in pending):
            target = next(f["field"] for f in pending if f.get("type") == "number")

    state["collected"][target] = text
    state["waiting"] = None
    return target


def track_complaint(complaint_id: str, ctx) -> dict:
    row = db.get_complaint(complaint_id or "")
    if not row:
        return {
            "found": False,
            "message_ml": "ആ പരാതി ഐഡി കണ്ടെത്താനായില്ല. പുതിയ പരാതി രജിസ്റ്റർ ചെയ്യാം.",
        }
    return {
        "found": True,
        "id": row["id"],
        "status": row["status"],
        "submitted_at": row["submitted_at"],
        "department": row["department"],
        "detail": row["detail"],
        "officer": row["officer"],
    }


def register_complaint(detail: str, department: str = "", ctx: dict | None = None) -> dict:
    cid = db.register_complaint(detail or "", department or "")
    return {
        "registered": True,
        "complaint_id": cid,
        "status": "Registered",
        "message_ml": f"നിങ്ങളുടെ പരാതി രജിസ്റ്റർ ചെയ്തു. ഡ്യൂട്ടി നമ്പർ: {cid}",
    }


def submit_application(service_id: str, answers, ctx) -> dict:
    service = kb.get_service(service_id or "")
    if not service:
        return {"error": f"unknown service_id: {service_id}"}
    payload = _flatten(service, answers)
    fields = service.get("form_fields", [])
    missing = [f for f in fields if not payload.get(f["field"])]
    if missing:
        labels = "; ".join(f.get("label_ml") or f["field"] for f in missing)
        return {
            "submitted": False,
            "missing_fields_ml": labels,
            "message_ml": "കുറച്ച് വിവരങ്ങൾ കൂടി ആവശ്യമാണ്. ഫോം വിസാർഡ് തുടരുക.",
        }
    app_no = db.create_application(ctx["session_id"], service_id, payload)
    return {
        "submitted": True,
        "application_no": app_no,
        "service_name_ml": service.get("name_ml"),
        "status": "Submitted",
        "submitted_at": None,
        "payload": payload,
        "next_steps_ml": service.get("steps", []),
        "portal": service.get("portal"),
        "center": {"name_ml": kb.center_info(service.get("center", "online")).get("name_ml", "")},
        "message_ml": f"അപേക്ഷ വിജയകരമായി സമർപ്പിച്ചു! രസീത് നമ്പർ: {app_no}",
    }


def track_application(application_no: str, ctx) -> dict:
    row = db.get_application(application_no or "")
    if not row:
        return {
            "found": False,
            "message_ml": "ആ അപേക്ഷ നമ്പർ കണ്ടെത്താനായില്ല. ഒരിക്കൽ കൂടി പരിശോധിക്കാമോ?",
        }
    return {
        "found": True,
        "application_no": row["id"],
        "service_id": row["service_id"],
        "status": row["status"],
        "submitted_at": row["submitted_at"],
    }


def route_to_department(service_id: str, ctx) -> dict:
    service = kb.get_service(service_id or "")
    if not service:
        return {"error": f"unknown service_id: {service_id}"}
    center = kb.center_info(service.get("center", "online"))
    return {
        "service_name_ml": service.get("name_ml"),
        "department": service.get("department"),
        "portal": service.get("portal"),
        "center_name_ml": center.get("name_ml", ""),
        "center_note_ml": center.get("note_ml", ""),
    }


def save_profile(key: str, value: str, ctx) -> dict:
    db.set_profile(ctx["session_id"], key, value)
    return {"saved": True, "key": key, "value": value}


def get_user_profile(_args, ctx) -> dict:
    return {"profile": db.get_profile(ctx["session_id"])}


def setup_profile(answers, ctx) -> dict:
    sid = ctx["session_id"]
    saved = db.get_profile(sid)
    given = _flatten({}, answers)

    for k, v in given.items():
        if v is not None and str(v).strip():
            db.set_profile(sid, k, str(v).strip())
            saved[k] = str(v).strip()

    remaining = [f for f in config.PROFILE_FIELDS if not saved.get(f["field"])]
    if remaining:
        nxt = remaining[0]
        return {
            "done": False,
            "current_field": nxt["field"],
            "current_field_label_ml": nxt["label_ml"],
            "current_field_label_en": nxt["label_en"],
            "progress_ml": f"{len(config.PROFILE_FIELDS) - len(remaining)}/{len(config.PROFILE_FIELDS)}",
        }
    return {
        "done": True,
        "profile": saved,
        "message_ml": "നിങ്ങളുടെ വിവരങ്ങൾ രജിസ്റ്റർ ചെയ്തു! ഇനി എല്ലാ അർഹതാ പരിശോധനകളും ഈ വിവരങ്ങൾ ഉപയോഗിച്ച് നടക്കും.",
        "message_en": "Your profile is saved! All eligibility checks will now use it.",
    }


def set_reminder(topic: str, remind_date: str, ctx) -> dict:
    db.add_reminder(ctx["session_id"], topic or "", remind_date or "")
    return {
        "saved": True,
        "topic": topic or "",
        "remind_date": remind_date or "",
        "message_ml": "ഓർമ്മപ്പെടുത്തൽ സജ്ജമാക്കി. കൃത്യസമയത്ത് അറിയിക്കാം.",
    }


# ---------------- Browser-driven portal automation ----------------

def browser_open(url: str = "", ctx: dict | None = None) -> dict:
    return browser.browser.open(url)


def browser_fill(label: str, value: str, ctx: dict | None = None) -> dict:
    return browser.browser.fill(label, value)


def browser_click(text: str, ctx: dict | None = None) -> dict:
    return browser.browser.click(text)


def browser_page_text(_args, ctx: dict | None = None) -> dict:
    return {"text": browser.browser.text()["text"]}


def browser_status(_args, ctx: dict | None = None) -> dict:
    return browser.browser.status()


def browser_close(_args, ctx: dict | None = None) -> dict:
    browser.browser.close()
    return {"closed": True}


TOOL_HANDLERS = {
    "search_service": search_service,
    "list_services": list_services,
    "check_eligibility": check_eligibility,
    "run_form_wizard": run_form_wizard,
    "track_complaint": track_complaint,
    "register_complaint": register_complaint,
    "submit_application": submit_application,
    "track_application": track_application,
    "route_to_department": route_to_department,
    "save_user_profile_field": save_profile,
    "get_user_profile": get_user_profile,
    "setup_profile": setup_profile,
    "set_reminder": set_reminder,
    "browser_open": browser_open,
    "browser_fill": browser_fill,
    "browser_click": browser_click,
    "browser_page_text": browser_page_text,
    "browser_status": browser_status,
    "browser_close": browser_close,
}


def run_tool(name: str, arguments: str, ctx: dict):
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"unknown tool: {name}"}
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if not isinstance(args, dict):
        args = {"value": args}

    params = inspect.signature(handler).parameters
    kwargs = {}
    for key, val in args.items():
        if key in params:
            kwargs[key] = val
    if "_args" in params:
        kwargs["_args"] = args
    if "ctx" in params:
        kwargs["ctx"] = ctx

    try:
        return handler(**kwargs)
    except TypeError as e:
        return {"error": f"tool {name} invoked with wrong arguments: {e}"}
    except Exception as e:  # a tool bug must never kill the whole reply
        return {"error": f"tool {name} failed: {e}"}


_register(
    name="search_service",
    description="Search the Kerala civic services knowledge base for a government service. Use this FIRST for any question about services, documents, eligibility, or steps.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Service name in English or Malayalam"}},
        "required": ["query"],
    },
)

_register(
    name="list_services",
    description="List all civic services this agent supports.",
    parameters={"type": "object", "properties": {}},
)

_register(
    name="check_eligibility",
    description="Evaluate whether the user qualifies for a service. Pass service_id and the answers the user gave to the eligibility questions.",
    parameters={
        "type": "object",
        "properties": {
            "service_id": {"type": "string", "description": "id from the knowledge base (e.g. ration_card)"},
            "answers": {"type": "object", "description": "field -> value per the eligibility questions"},
        },
        "required": ["service_id", "answers"],
    },
)

_register(
    name="run_form_wizard",
    description="Drive the application form for a service step by step. Pass service_id and ONLY the latest field answers the user provided. It returns the next question to ask. Re-invoke it each time the user answers another field.",
    parameters={
        "type": "object",
        "properties": {
            "service_id": {"type": "string"},
            "answers": {"type": "object", "description": "latest field -> value"},
        },
        "required": ["service_id", "answers"],
    },
)

_register(
    name="track_complaint",
    description="Get the current status of a complaint by its receipt/complaint ID.",
    parameters={
        "type": "object",
        "properties": {"complaint_id": {"type": "string"}},
        "required": ["complaint_id"],
    },
)

_register(
    name="register_complaint",
    description="Register a NEW complaint in the grievance system and return a complaint ID.",
    parameters={
        "type": "object",
        "properties": {
            "detail": {"type": "string", "description": "Complaint description"},
            "department": {"type": "string", "description": "Department to complain about"},
        },
        "required": ["detail"],
    },
)

_register(
    name="submit_application",
    description="SUBMIT a completed application for a service. Call this right after run_form_wizard reports done=True, passing the full collected payload. Returns a receipt number (SEV-...) the citizen can quote anywhere.",
    parameters={
        "type": "object",
        "properties": {
            "service_id": {"type": "string"},
            "answers": {"type": "object", "description": "the complete field -> value payload collected by the wizard"},
        },
        "required": ["service_id", "answers"],
    },
)

_register(
    name="track_application",
    description="Check the live status of a submitted application by its receipt number (SEV-...).",
    parameters={
        "type": "object",
        "properties": {"application_no": {"type": "string"}},
        "required": ["application_no"],
    },
)

_register(
    name="route_to_department",
    description="Direct the user to the department, portal and service centre for a service.",
    parameters={
        "type": "object",
        "properties": {"service_id": {"type": "string"}},
        "required": ["service_id"],
    },
)

_register(
    name="save_user_profile_field",
    description="Save a personal fact about the user (name, district, family size, etc.) so it is remembered later.",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"],
    },
)

_register(
    name="get_user_profile",
    description="Get everything remembered about this user.",
    parameters={"type": "object", "properties": {}},
)

_register(
    name="setup_profile",
    description="Sign-up / profile setup wizard. Call it when the user wants to register their details (or when their profile is mostly empty). Pass the latest field answer(s) only. It returns the next profile question to ask. Re-invoke it as each answer arrives, SAVING each field into the profile automatically. Always call get_user_profile before eligibility checks and supply saved profile facts as the answers.",
    parameters={
        "type": "object",
        "properties": {
            "answers": {"type": "object", "description": "latest profile field -> value"},
        },
        "required": ["answers"],
    },
)

_register(
    name="set_reminder",
    description="Set a reminder/follow-up for the user (e.g. to submit documents).",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "remind_date": {"type": "string", "description": "date like 2026-09-20"},
        },
        "required": ["topic", "remind_date"],
    },
)

_register(
    name="browser_open",
    description="Open a government portal URL in the visible browser window. Use the service's portal URL when known.",
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "full URL, e.g. https://supplies.kerala.gov.in"}},
        "required": ["url"],
    },
)

_register(
    name="browser_fill",
    description="Type a value into a form field in the open browser. Pass the field label shown on the page (or its label/placeholder text).",
    parameters={
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "the field's label or placeholder text as seen on the page"},
            "value": {"type": "string", "description": "text to type into the field"},
        },
        "required": ["label", "value"],
    },
)

_register(
    name="browser_click",
    description="Click a button or link on the open page by its visible text.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "button/link text"}},
        "required": ["text"],
    },
)

_register(
    name="browser_page_text",
    description="Read the visible text of the current browser page. Call after opening a page or clicking to see what happened.",
    parameters={"type": "object", "properties": {}},
)

_register(
    name="browser_status",
    description="Check the browser state: current URL, title, loading status, and whether the page is asking the user for login/OTP/captcha.",
    parameters={"type": "object", "properties": {}},
)

_register(
    name="browser_close",
    description="Close the browser window.",
    parameters={"type": "object", "properties": {}},
)