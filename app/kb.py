import json
import os
import unicodedata

_KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "services.json")


def _load():
    with open(_KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s.lower())
    return "".join(ch for ch in s if ch.isalnum())


def get_all_services() -> list:
    return _load()["services"]


def get_service(service_id: str) -> dict | None:
    for svc in get_all_services():
        if svc["id"] == service_id:
            return svc
    return None


def resolve_service_id(query: str) -> str | None:
    q = _norm(query)
    if not q:
        return None
    for svc in get_all_services():
        haystack = [svc["id"], svc["name_en"], svc["name_ml"],
                    svc["department"]] + list(svc.get("aliases", []))
        if any(_norm(h) and _norm(h) in q for h in haystack):
            return svc["id"]
        if any(q in _norm(h) for h in haystack):
            return svc["id"]
    return None


def search_services(query: str) -> list:
    svc_id = resolve_service_id(query)
    if not svc_id:
        return []
    return [get_service(svc_id)]


def center_info(center_key: str) -> dict:
    return _load()["service_center"].get(center_key, {})


def _to_bool(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = _norm(str(v))
    if s in ("true", "yes", "y", "1", "ഉണ്ട്", "അതെ", "ഉണ"):
        return True
    if s in ("false", "no", "n", "0", "ഇല്ല", "അല്ല"):
        return False
    return None


def _to_number(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").replace("₹", "").replace("रू", "").strip())
    except (TypeError, ValueError):
        return None


def _eval_rule(rule: dict, answers: dict) -> bool:
    op = rule.get("op")
    args = rule.get("args", [])
    if op == "gte":
        a, b = _to_number(answers.get(args[0])), _to_number(args[1])
        return a is not None and a >= b
    if op == "lte":
        a, b = _to_number(answers.get(args[0])), _to_number(args[1])
        return a is not None and a <= b
    if op == "eq":
        return _to_bool(answers.get(args[0])) == _to_bool(args[1])
    if op == "neq":
        return _to_bool(answers.get(args[0])) != _to_bool(args[1])
    return True


def check_eligibility(service: dict, answers: dict) -> dict:
    results = []
    for rule in service.get("eligibility", []):
        passed = _eval_rule(rule.get("rule", {}), answers)
        results.append(
            {
                "field": rule["field"],
                "question_ml": rule.get("question_ml", ""),
                "question_en": rule.get("question_en", ""),
                "pass": passed,
                "failure_note_ml": rule.get("failure_note_ml", ""),
                "failure_note_en": rule.get("failure_note_en", ""),
            }
        )
    docs = service.get("documents", [])
    docs_en = service.get("documents_en", [])
    return {
        "service_name_ml": service.get("name_ml"),
        "department": service.get("department"),
        "all_pass": all(r["pass"] for r in results),
        "results": results,
        "documents_ml": docs,
        "documents_en": docs_en,
    }


def summarize_service(service: dict) -> dict:
    return {
        "id": service.get("id"),
        "name_ml": service.get("name_ml"),
        "name_en": service.get("name_en"),
        "department": service.get("department"),
        "portal": service.get("portal"),
        "summary_ml": service.get("summary_ml"),
        "summary_en": service.get("summary_en"),
        "eligibility_questions": service.get("eligibility", []),
        "documents_ml": service.get("documents", []),
        "documents_en": service.get("documents_en", []),
        "steps_ml": service.get("steps", []),
        "center": service.get("center"),
        "form_fields": service.get("form_fields", []),
    }