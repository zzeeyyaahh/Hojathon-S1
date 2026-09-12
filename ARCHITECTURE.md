# Sevana Voice — Malayalam Civic Agent
**Hoja Techademy Agentic AI Hackathon 2026 · Public Services & Civic Agents**

---

## 1. Vision

A **voice-first, Malayalam-speaking civic agent** that helps people interact with
Kerala government services **without understanding government procedures**.

The agent does more than chat — it is a real **agent**:
- **Understands a goal** (e.g. "എനിക്ക് റേഷൻ കാർഡ് വേണം") 
- **Remembers** the conversation and builds a user profile (age, district, ration card status...)
- **Decides** which tool to call (eligibility check, form wizard, complaint lookup, department routing)
- **Uses tools** to give grounded answers (no hallucination)
- **Takes action** — collects form fields step-by-step, tracks progress, returns a filled form payload, and can follow up

Demo language: Malayalam-first, code-mixed with English technical terms (realistic for Kerala).

---

## 2. Why this wins

| Problem statement asks for | Our answer |
|---|---|
| Fill out forms | **Form Wizard** tool — collects fields one by one, keeps progress, returns structured data ready for the real portal |
| Check eligibility | **Eligibility Engine** — rule-based over a knowledge base, explains doc-by-doc |
| Track complaints | **Complaint Tracker** — id lookup into a local store + real-portal API stub |
| Direct to right department | **Department Router** — from KB, maps service → department → Seva Kendram/Akshaya center |
| Remember relevant information | Session memory + persistent **user profile** (SQLite) |
| Make decisions & take actions | LLM **tool-calling loop** (not a plain chatbot) |
| Malayalam voice | Web Speech API (`ml-IN`) + edge-tts neural voice + Groq Whisper fallback |

---

## 3. High-level architecture

```
┌─────────────────────────────── PRESENTATION ───────────────────────────────┐
│  Mobile-first Web UI (HTML/CSS/JS, single page)                            │
│  · Big "Tap to speak" mic · Malayalam voice in (Web Speech API ml-IN)      │
│  · Malayalam voice out (edge-tts audio) · Chat transcript · Text fallback │
│  · Form-progress cards · Eligibility report · Complaint status widgets     │
└─────────────────────────────────┬─────────────────────────────────────────┘
                                  │ HTTP / JSON
┌─────────────────────────────── API LAYER (FastAPI) ─────────────────────────┐
│  POST /api/session    create/reset session (returns session_id)            │
│  POST /api/chat       {session_id, text} → {reply, audio_url, status}      │
│  POST /api/asr        audio file → Malayalam text (Groq Whisper fallback)  │
│  GET  /api/tts/{text} → mp3 (edge-tts, cached)                             │
│  GET  /api/status     service/outage health (for demo)                     │
└─────────────────────────────────┬─────────────────────────────────────────┘
┌────────────────────────────── AGENT LAYER ──────────────────────────────────┐
│  Orchestrator loop:                                                        │
│   1. LLM sees {system prompt + tools schema + history + user profile}       │
│   2. LLM returns reply AND/OR tool_call                                     │
│   3. run tool → result appended to context → loop                           │
│   4. loop ends when LLM yields a final reply                                │
│  Memory: session dict + persistent SQLite user profile                      │
│  Guardrails: grounded search first; form wizard has explicit steps          │
└─────────────────────────────────┬─────────────────────────────────────────┘
┌────────────────────────── TOOLS & SERVICES ─────────────────────────────────┐
│  search_service(q)          → KB lookup (grounded facts)                    │
│  check_eligibility(service, profile) → rule engine result                   │
│  run_form_wizard(service, fields_so_far, answers) → progress + next field   │
│  track_complaint(id)        → complaint store / portal API stub             │
│  route_to_dept(service)     → department + Seva Kendram/Akshaya center      │
│  save_profile(field, value) → persist learned user facts                    │
│  fetch_services(kb)         → list of all services (for "what can you do?") │
└─────────────────────────────────┬─────────────────────────────────────────┘
┌────────────────────────────── DATA LAYER ───────────────────────────────────┐
│  kb/services.json      (8–12 Kerala services: dept, eligibility, docs,      │
│                         steps, forms, center type)                          │
│  db/citizens.db (SQLite)  user_profiles · complaints · form_sessions        │
│  static/tts cache          generated Malayalam voice clips                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technology choices (all free, hackathon-safe)

| Concern | Choice | Why |
|---|---|---|
| Web server / API | **FastAPI + uvicorn** | Modern, async, one-file simple, auto docs |
| Agent brain (LLM) | **Groq** `llama-3.3-70b-versatile` (free tier, tool calling) | Fast, generous free tier, OpenAI-compatible API |
| Fallback brain | **Google Gemini** `gemini-2.0-flash` | Excellent Malayalam, free tier |
| Speech→Text (ASR) | **Web Speech API** `lang='ml-IN'` in Chrome (real-time, zero backend) | Instant, free native Malayalam |
| ASR fallback | **Groq Whisper** `whisper-large-v3-turbo` | Free, accurate Malayalam from audio file |
| Text→Speech (TTS) | **edge-tts** `ml-IN-SobhanaNeural` | Free neural Malayalam voice, much better than gTTS |
| TTS fallback | **gTTS** `ml` | Free, no extra deps |
| DB | **SQLite** (stdlib) | Zero setup, persistence |
| Frontend | Vanilla HTML/CSS/JS page served by FastAPI | Zero build step, full control of voice UX |

**Why no LangGraph/CrewAI:** your agent loop is ~60 lines. A hand-rolled
loop is easier to debug, demo, and explain to judges — and one less dependency
to break. We can mention the pattern as agentic RAG + tool use.

---

## 5. Data model

### `kb/services.json` — one entry per civic service
```json
{
  "id": "ration_card",
  "name_ml": "റേഷൻ കാർഡ്",
  "name_en": "Ration Card / PDS",
  "department": "Civil Supplies Department",
  "portal": "https://supplies.kerala.gov.in",
  "aliases": ["ration", "rashi card", "pds", "ഭക്ഷ്യസുരക്ഷാ കാർഡ്"],
  "summary_ml": "അർഹരായ കുടുംബങ്ങൾക്ക് സബ്സിഡി നിരക്കിൽ ഭക്ഷ്യധാന്യം...",
  "eligibility": [
    {"condition": "APL/BPL family status decided by government survey", "rule": "family_survey_state exists"}
  ],
  "documents": ["Aadhaar", "Ration card copy of head", "Address proof", "Income certificate"],
  "steps": [
    "Get e-Services ID from Akshaya Centre",
    "Apply via Sevana portal with documents",
    "Field verification by Supply Inspector",
    "Receive card at local supplier / KSFE office"
  ],
  "form_fields": ["applicant_name", "aadhaar", "address", "family_size", "income_slab", "district"],
  "center": "aksaya"
}
```

### `citizens.db` tables
```sql
user_profiles(session_id TEXT, key TEXT, value TEXT, updated_at)
complaints(id TEXT PRIMARY KEY, status TEXT, submitted_at, detail, officer)
form_sessions(session_id TEXT, service_id TEXT, stage INT, answers TEXT, done INT)
```

---

## 6. Agent loop (core logic)

Pseudocode that runs per user turn:

```
1. load memory: session history + user profile (SQLite)
2. build prompt:
     system = PROJECT_SYSTEM_PROMPT + KB summary ("you know these N services...")
     user   = latest utterance
3. call LLM(messages, tools=[tool1..tool8])
4. if response.tool_calls:
     for each call: result = execute_tool(call)
        if call is run_form_wizard or check_eligibility:
            result also updates DB / session state
        append tool result to messages
     go back to 3        # re-call LLM with results
5. else: final reply text
6. save session history + updated profile
7. return reply + (optional) widget JSON for frontend
```

**Guardrails** so it never hallucinates:
- Facts come only from `search_service` (KB) or `track_complaint` (DB) results — never from memory.
- Form wizard is state-machine driven: the LLM only forwards user answers; the tool decides next question.
- If user asks something outside civic services, agent politely redirects.

---

## 7. Tool schemas (what the LLM can call)

| Tool | Input | Output | Purpose |
|---|---|---|---|
| `search_service(query)` | query string | service object from KB (or null) | grounded facts |
| `list_services()` | — | all service names | "what can you help with?" |
| `check_eligibility(service_id, answers)` | answers dict | pass/fail + reasons + missing docs | eligibility decision |
| `run_form_wizard(service_id, step_answers)` | dict | next question + progress + final payload | form filling |
| `track_complaint(complaint_id)` | id | status/detail/officer | complaint tracking |
| `route_to_department(service_id)` | id | dept + portal + nearest center type | routing |
| `save_profile(key, value)` | key/value | ok | memory |
| `get_profile()` | — | profile dict | personalisation |

---

## 8. Build plan (phases, each testable)

### Phase 0 — Setup (~20 min)
- venv, `requirements.txt`, `.env` (GROQ_API_KEY), folder layout.

### Phase 1 — Knowledge base (~1 hr)
- Write `services_kb.py` with 10 Kerala services: Ration Card, Birth Certificate, Death Certificate, Income Certificate, Welfare Pension, Passport Tata/Sevana, Scholarship (SSP), e-District complaints, Property Tax, UID/Aadhaar update.
- `check_eligibility` + `route_to_department` pure functions with unit tests.

### Phase 2 — Agent core (~1.5 hr)
- `llm.py`: Groq client + fallback Gemini.
- `agent.py`: the loop from §6, `memory.py` (session + profile), tool registry.

### Phase 3 — Voice (~1 hr)
- `tts.py`: edge-tts → cache mp3 → `/api/tts`.
- Frontend: Web Speech API `ml-IN` capture → send text to `/api/chat`.
- `asr.py` fallback: `/api/asr` via Groq Whisper for uploaded audio / non-Chrome.

### Phase 4 — Backend endpoints + frontend UI (~2 hr)
- FastAPI app: `/api/*` endpoints, CORS, serve static page.
- Mobile-first UI: header + mic button + transcript bubbles + widget cards + form progress bar.
- Malayalam UI labels, big touch targets.

### Phase 5 — Polish & demo (~1 hr)
- Seed complaint store with 2–3 fake complaints for the demo.
- Demo script (judge-safe), README, `run.bat`/`run.sh`.
- Optional stretch: deploy to free hosting (Render) so judges can open on their phone.

---

## 9. Demo script (3 minutes)

1. Open app in Chrome on a laptop (localhost). Say "ഞാൻ റേഷൻ കാർഡിന് അപേക്ഷിക്കാൻ ഉദ്ദേശിക്കുന്നു".
2. Agent asks for district → user says "എറണാകുളം" → agent builds profile.
3. Agent runs `check_eligibility`, shows ✅/❌ reasons + missing documents as a card.
4. Say "എന്റെ പരാതി എന്ത് നിലയിലാണ്?" with a pre-seeded complaint ID → agent shows live status.
5. Say "എവിടെ പോയി അപേക്ഷിക്കണം?" → agent routes to Akshaya Centre near the user.
6. Ask the form wizard to start → watch it collect fields one-by-one with progress.
7. Close: "ഞാൻ നിങ്ങൾക്ക് ഒരു ഓർമ്മപ്പെടുത്തൽ സജ്ജമാക്കാം" (reminder) → agent sets a follow-up (shows memory/autonomy).

Judge notes: *grounded (no hallucination)*, *stateful (remembers)*, *tool-driven actions (not just chat)*, *Malayalam voice-first*.

---

## 10. Risks & fallbacks

| Risk | Mitigation |
|---|---|
| Web Speech API unavailable (Firefox/Edge) | Text input always visible + `/api/asr` via Groq Whisper |
| edge-tts network hiccup | gTTS fallback; in browser `speechSynthesis` fallback |
| Groq rate limits | Gemini fallback; both are free until demo limit |
| Mic requires secure context | Demo on `localhost` (Chrome allows); for LAN demo use HTTPS tunnel (cloudflared) |
| LLM hallucination | Grounded tool-first guardrail + KB summary in system prompt |