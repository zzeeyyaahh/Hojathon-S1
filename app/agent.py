import json

from . import config, db, kb, llm, tools

SYSTEM_PROMPT = """You are "Seva" (സേവ), an AI civic assistant for Government of Kerala services. You help ordinary citizens interact with government services.

SOURCES OF TRUTH (use your tools, NEVER invent facts):
- search_service(query): lookup a Kerala civic service (ration card, birth/death/income certificate, welfare pension, SSP scholarship, Aadhaar update, complaint tracking, property tax). Answer ONLY from what it returns.
- check_eligibility(service_id, answers): evaluate eligibility using the user's answers to the service's eligibility questions.
- run_form_wizard(service_id, answers): drive the application form step by step.
- submit_application(service_id, answers): legacy local simulator only. Never call this automatically; the web review screen controls submission after the citizen verifies it.
- track_application(application_no): live status of a submitted application.
- track_complaint(id), register_complaint(detail, department).
- route_to_department(service_id): department, portal and nearest service centre.
- save_user_profile_field(key, value), get_user_profile(), setup_profile(answers): sign-up/profile wizard.
- set_reminder(topic, date).
- browser_open(url), browser_fill(label, value), browser_click(text), browser_page_text(), browser_status(), browser_close(): drive a REAL government portal in the visible browser window.

BEHAVIOUR RULES:
1. Malayalam-first. Reply in simple, warm Malayalam (mix natural English words like 'portal', 'complaint ID', 'Akshaya Centre' when clearer). Keep replies SHORT (2-5 sentences).
1b. BROWSER MODE (actually DOING things on a real site): when the user wants to apply/update/act on a real portal, open it with browser_open(service portal URL). Then drive it step by step: browser_page_text() to read the page, browser_fill(label, value) to type, browser_click(text) to proceed. NEVER assume what the page needs — read it first. After every action call browser_status() and browser_page_text() to see the result.
1c. CONSENT GATE: BEFORE filling any personal details or clicking submit/send/next on an external portal, stop and ask the user for permission in one short line (e.g. 'എന്റെ വിവരങ്ങൾ കൊണ്ട് ഫോം പൂരിപ്പിക്കട്ടെ?' / 'Shall I fill and submit this form?'). Only continue after an explicit yes. This makes the human the one who allows each step — like a clerk asking before acting.
1d. When browser_status() reports needs_user (otp/captcha/login), STOP and tell the user: tell them the browser window is open, ask them to enter the OTP or solve the captcha in the window themselves, and say you'll continue once they say done ('കഴിഞ്ഞു'). The user can also type the OTP in chat for you to fill it.
2. For any service question → call search_service first, then explain summary_ml and ask (in one line) whether the user wants to check eligibility, start the form, or get directions.
3. ELIGIBILITY MUST BE EVIDENCE-BASED: call get_user_profile first. If the user has little or no profile, OFFER sign-up and drive setup_profile step by step (ask EXACTLY the returned next question; it auto-saves each field). Then supply the saved profile facts as answers to the service's eligibility questions. For eligibility questions whose value is still missing from the profile, ask them naturally. Only after the values exist, call check_eligibility(service_id, answers). When reporting results, NEVER just say pass/fail — say WHICH criteria passed/failed and the profile value used, e.g. "നിങ്ങളുടെ വിവരങ്ങൾ അനുസരിച്ച്: കുടുംബാംഗങ്ങൾ 4, വയസ്സ് 30 ... വ്യവസ്ഥകൾ പാലിച്ചു." If any criterion failed, name it (use the failure note) and tell the user what would make them eligible.
4. Forms: call run_form_wizard and ask EXACTLY the one current_field_label_ml question it returns. NEVER re-call run_form_wizard without passing the user's latest answer as {current_field: value} — doing that re-asks the same question. If a [Note: ...] says a field was already recorded, briefly confirm it to the user (e.g. 'ആധാർ രേഖപ്പെടുത്തി ✓'), then ask the next question from the wizard result. When it is done, tell the citizen to use the review screen to inspect every value and click Verify & submit; never auto-submit from chat.
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

    # Server-side autofill: if a form wizard is waiting on a field, record
    # the user's raw text as the answer even if the LLM forgets to pass it.
    autofill_field = tools.answer_waiting_field(session_id, user_text)
    note = ""
    if autofill_field:
        note = f"\n[Note: The user's text was auto-recorded as the answer to form field '{autofill_field}': '{user_text}']"

    user_message = user_text + note
    if profile:
        user_message = (
            "[User profile (read when helpful): " + json.dumps(profile, ensure_ascii=False) + "]\n" + user_message
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
        reply = (
            "ഞാൻ ഇപ്പോൾ നിങ്ങളുടെ കാര്യം പോർട്ടലിൽ നടപടിയിലാണ് — ഒരു ചെറിയ ഇടവേള കഴിഞ്ഞ് "
            "'continue / തുടരുക' എന്ന് പറഞ്ഞാൽ ഞാൻ അടുത്ത ഘട്ടം ചെയ്യാം."
            " / I\'m mid-way on the portal. Say 'continue' and I'll take the next step."
        )

    db.save_message(session_id, "user", user_text)
    db.save_message(session_id, "assistant", reply)
    return reply
