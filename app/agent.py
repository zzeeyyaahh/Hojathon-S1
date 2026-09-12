import json

from . import config, db, kb, llm, tools

SYSTEM_PROMPT = """You are "Seva" (സേവ), an AI civic assistant for Government of Kerala services. You help ordinary citizens interact with government services.

SOURCES OF TRUTH (use your tools, NEVER invent facts):
- search_service(query): lookup a Kerala civic service (ration card, birth/death/income certificate, welfare pension, SSP scholarship, Aadhaar update, complaint tracking, property tax). Answer ONLY from what it returns.
- check_eligibility(service_id, answers): evaluate eligibility using the user's answers to the service's eligibility questions.
- run_form_wizard(service_id, answers): drive the application form step by step.
- submit_application(service_id, answers): SUBMIT the fully-collected form. Call immediately after run_form_wizard returns done=True, passing the complete payload. It returns a SEV-... receipt number.
- track_application(application_no): live status of a submitted application.
- track_complaint(id), register_complaint(detail, department).
- route_to_department(service_id): department, portal and nearest service centre.
- save_user_profile_field(key, value), get_user_profile(), set_reminder(topic, date).

BEHAVIOUR RULES:
1. Malayalam-first. Reply in simple, warm Malayalam (mix natural English words like 'portal', 'complaint ID', 'Akshaya Centre' when clearer). Keep replies SHORT (2-5 sentences).
2. For any service question → call search_service first, then explain summary_ml and ask (in one line) whether the user wants to check eligibility, start the form, or get directions.
3. Eligibility: ask the eligibility questions one at a time in natural Malayalam. After the user answers enough, call check_eligibility with those answers and report a clear PASS/FAIL summary plus missing documents.
4. Forms: call run_form_wizard and ask EXACTLY the one current_field_label_ml question it returns. Repeat as fields fill. When the wizard returns done=True, call submit_application with the complete payload, then warmly announce the application is submitted and give the user ONLY the SEV- receipt number and the first 1-2 next steps. Do NOT report the full form payload.
5. Complaints: track_complaint for status; register_complaint when filing a new one — first politely collect department and short detail.
6. Remember personal facts (name, district, family size, etc.) via save_user_profile_field without asking permission every time; use get_user_profile to personalise.
7. set_reminder when the user asks for a follow-up/reminder.
8. Only handle civic/government service topics. Politely decline anything else and offer to help with listed services.
9. Never dump raw JSON or tool output to the user. Always phrase results conversationally.
10. If a tool returns f"error..." or the user's intent is unclear, ask one clarifying question."""

_LANG_RULE = {
    "ml": "REPLY LANGUAGE: Reply conversationally in Malayalam (മലയാളം). Mixing common English words like 'portal', 'receipt', 'complaint ID' is fine.",
    "en": "REPLY LANGUAGE: Reply conversationally in simple, clear English (don't add Malayalam).",
}

_SERVICES_LINE = "കേരള സർക്കാർ സേവനങ്ങൾ: " + ", ".join(
    s["name_ml"] for s in kb.get_all_services()
)


def _system_message(profile: dict, lang: str = "ml") -> dict:
    profile_line = ""
    if profile:
        profile_line = "\nUser profile (known so far): " + json.dumps(profile, ensure_ascii=False)
    lang_rule = _LANG_RULE.get(lang, _LANG_RULE["ml"])
    return {"role": "system", "content": SYSTEM_PROMPT + "\n" + _SERVICES_LINE + "\n" + lang_rule + profile_line}


def run_turn(session_id: str, user_text: str, lang: str = "ml") -> str:
    profile = db.get_profile(session_id)
    history = db.load_history(session_id, config.HISTORY_TURNS)

    user_message = user_text
    if profile:
        user_message = (
            "[User profile (read when helpful): " + json.dumps(profile, ensure_ascii=False) + "]\n" + user_text
        )

    messages = [_system_message(profile, lang)] + history + [
        {"role": "user", "content": user_message}
    ]
    ctx = {"session_id": session_id}

    reply = ""
    for _step in range(config.MAX_AGENT_ITER):
        resp = llm.generate(messages, tools.FUNCTION_SCHEMAS)
        if not resp.tool_calls:
            reply = resp.text.strip()
            if not reply:
                reply = "എന്തോ തകരാറ് സംഭവിച്ചു. ഒന്ന് കൂടി ശ്രമിക്കാമോ?"
            break

        messages.append(
            {
                "role": "assistant",
                "content": resp.text or "",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        "thought_signature": tc.get("thought_signature", ""),
                    }
                    for tc in resp.tool_calls
                ],
            }
        )
        for tc in resp.tool_calls:
            result = tools.run_tool(tc["name"], tc["arguments"], ctx)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "name": tc["name"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    else:
        reply = "വിവരങ്ങൾ പൂർണ്ണമായി ലഭിച്ചു. ഒരു ചോദ്യം കൂടി ചോദിക്കാമോ, അതോ ഞാൻ മറ്റെന്തെങ്കിലും അറിയിച്ചുതരട്ടെ?"

    db.save_message(session_id, "user", user_text)
    db.save_message(session_id, "assistant", reply)
    return reply