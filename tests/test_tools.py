import json
import sys

sys.path.insert(0, r"C:\Users\hp\Desktop\hoja")

from app import db, tools

db.init_db()
ctx = {"session_id": "t1"}


def tool(name, args):
    return tools.run_tool(name, json.dumps(args, ensure_ascii=False), ctx)


r = tool("search_service", {"query": "റേഷൻ കാർഡ്"})
assert r["found"] is True and r["service"]["id"] == "ration_card", r

r = tool("search_service", {"query": "pension"})
assert r["found"] and r["service"]["id"] == "welfare_pension", r

r = tool(
    "check_eligibility",
    {"service_id": "ration_card",
     "answers": {"family_size": 4, "already_has_card": False, "family_survey_state": True}},
)
assert r["all_pass"] is True, r

r = tool(
    "check_eligibility",
    {"service_id": "welfare_pension", "answers": {"age": 40}},
)
assert r["all_pass"] is False and r["results"][0]["pass"] is False, r

r = tool("track_complaint", {"complaint_id": "GR-2026-1187"})
assert r["found"] and r["status"] == "Under investigation", r

r = tool("route_to_department", {"service_id": "welfare_pension"})
assert r["department"] and r["center_name_ml"], r

r = tool("run_form_wizard", {"service_id": "income_certificate", "answers": {"applicant_name": "Arjun"}})
assert r["current_field"] == "aadhaar" and r["done"] is False, r

r = tool("run_form_wizard", {"service_id": "income_certificate", "answers": {"aadhaar": "123456789012"}})
assert r["current_field"] == "address", r

r = tool("list_services", {})
assert len(r["services"]) >= 7, r

r = tool("register_complaint", {"detail": "street light not working", "department": "LSGD"})
assert r["registered"], r

r = tool("save_user_profile_field", {"key": "district", "value": "Ernakulam"})
assert r["saved"], r

r = tool("get_user_profile", {})
assert r["profile"].get("district") == "Ernakulam", r

print("ALL TOOL TESTS PASSED")