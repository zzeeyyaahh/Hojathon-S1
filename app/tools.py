import json

from . import db, kb

_WIZARDS: dict = {}

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
        state = {"service_id": service_id, "collected": {}}
        _WIZARDS[sid] = state

    collected = state["collected"]
    for k, v in _flatten({}, answers).items():
        collected[k] = v

    service = kb.get_service(service_id)
    if not service:
        return {"error": f"unknown service_id: {service_id}"}

    fields = service.get("form_fields", [])
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
        progress["current_field"] = nxt["field"]
        progress["current_field_label_ml"] = nxt.get("label_ml")
        progress["current_field_label_en"] = nxt.get("label_en")
        progress["done"] = False
        return progress

    progress["done"] = True
    progress["payload"] = {f["field"]: collected.get(f["field"]) for f in fields}
    progress["next_steps_ml"] = service.get("steps", [])
    progress["portal"] = service.get("portal")
    return progress


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


def set_reminder(topic: str, remind_date: str, ctx) -> dict:
    db.add_reminder(ctx["session_id"], topic or "", remind_date or "")
    return {
        "saved": True,
        "topic": topic or "",
        "remind_date": remind_date or "",
        "message_ml": "ഓർമ്മപ്പെടുത്തൽ സജ്ജമാക്കി. കൃത്യസമയത്ത് അറിയിക്കാം.",
    }


TOOL_HANDLERS = {
    "search_service": search_service,
    "list_services": list_services,
    "check_eligibility": check_eligibility,
    "run_form_wizard": run_form_wizard,
    "track_complaint": track_complaint,
    "register_complaint": register_complaint,
    "route_to_department": route_to_department,
    "save_user_profile_field": save_profile,
    "get_user_profile": get_user_profile,
    "set_reminder": set_reminder,
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
    try:
        return handler(**args, ctx=ctx)
    except TypeError:
        return handler(args, ctx)


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