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
     "answers": {"age": 35, "family_size": 4, "already_has_card": False, "family_survey_state": True}},
)
assert r["all_pass"] is True, r

r = tool(
    "check_eligibility",
    {"service_id": "ration_card",
     "answers": {"age": 3, "family_size": 4, "already_has_card": False, "family_survey_state": True}},
)
assert r["all_pass"] is False and r["results"][0]["field"] == "age" and r["results"][0]["pass"] is False, r

r = tool(
    "check_eligibility",
    {"service_id": "welfare_pension", "answers": {"age": 40}},
)
assert r["all_pass"] is False and r["results"][0]["pass"] is False, r

r = tool("track_complaint", {"complaint_id": "GR-2026-1187"})
assert r["found"] and r["status"] == "Under investigation", r

r = tool("route_to_department", {"service_id": "welfare_pension"})
assert r["department"] and r["center_name_ml"], r

r = tool(
    "submit_application",
    {"service_id": "income_certificate",
     "answers": {"applicant_name": "Arjun", "aadhaar": "123456789012",
                 "address": "Kakkanad, Ernakulam", "annual_income": "250000",
                 "purpose": "Scholarship"}},
)
assert r["submitted"] and r["application_no"].startswith("SEV-"), r
app_no = r["application_no"]

r = tool("submit_application", {"service_id": "income_certificate", "answers": {"applicant_name": "Arjun"}})
assert r["submitted"] is False and r["missing_fields_ml"], r

r = tool("track_application", {"application_no": app_no})
assert r["found"] and r["status"] == "Submitted", r

r = tool("track_application", {"application_no": "SEV-0000-0000"})
assert r["found"] is False, r

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

# Profile sign-up wizard (fresh session each run — DB is persistent)
import time as _t
ctx2 = {"session_id": "signtest-" + str(int(_t.time()))}

def tool2(name, args):
    return tools.run_tool(name, json.dumps(args, ensure_ascii=False), ctx2)

r = tool2("setup_profile", {"answers": {"name": "Anu"}})
assert r["done"] is False and r["current_field"] == "district", r

r = tool2("setup_profile", {"answers": {"district": "Kozhikode"}})
assert r["done"] is True and r["profile"]["name"] == "Anu", r

r = tool2("get_user_profile", {})
assert r["profile"]["district"] == "Kozhikode" and r["profile"]["name"] == "Anu", r

# Form wizard autofill: bare answer goes to the waiting field
ctx3 = {"session_id": "t3"}

def tool3(name, args):
    return tools.run_tool(name, json.dumps(args, ensure_ascii=False), ctx3)

r = tool3("run_form_wizard", {"service_id": "income_certificate", "answers": {}})
assert r["current_field"] == "applicant_name", r

assert tools.answer_waiting_field("t3", "Ravi") == "applicant_name"
r = tool3("run_form_wizard", {"service_id": "income_certificate", "answers": {}})
assert r["current_field"] == "aadhaar", r

assert tools.answer_waiting_field("t3", "425202563925") == "aadhaar"
r = tool3("run_form_wizard", {"service_id": "income_certificate", "answers": {"address": "Kochi"}})
assert r["current_field"] == "annual_income", r

print("ALL TOOL TESTS PASSED")