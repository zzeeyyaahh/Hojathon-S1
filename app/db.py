import os
import sqlite3
import uuid
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

_BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE, "..", "data", "citizens.db")

SEED_COMPLAINTS = [
    ("GR-2026-1042", "Resolved", "2026-07-18",
     "Kerala Water Authority",
     "Kakkanad ഭാഗത്ത് കുടിവെള്ള വിതരണം നിലച്ചു", "R. Suresh"),
    ("GR-2026-1187", "Under investigation", "2026-08-02",
     "Civil Supplies",
     "3 മാസമായി റേഷൻ കാർഡ് ലഭിച്ചിട്ടില്ല", "M. Lakshmi"),
    ("GR-2026-0931", "Action initiated", "2026-07-05",
     "LSGD",
     "സ്കൂളിന് സമീപം സ്ട്രീറ്റ് ലൈറ്റ് പ്രവർത്തിക്കുന്നില്ല", "Anil Kumar"),
]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _connect() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS users(
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS auth_tokens(
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS user_profiles(
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                updated_at TEXT,
                PRIMARY KEY(session_id, key))"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS complaints(
                id TEXT PRIMARY KEY,
                status TEXT,
                submitted_at TEXT,
                department TEXT,
                detail TEXT,
                officer TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS history(
                session_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                PRIMARY KEY(session_id, seq))"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS reminders(
                session_id TEXT NOT NULL,
                topic TEXT,
                remind_date TEXT,
                created_at TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS applications(
                id TEXT PRIMARY KEY,
                session_id TEXT,
                service_id TEXT,
                payload TEXT,
                status TEXT,
                submitted_at TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS application_drafts(
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                service_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                reviewed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL)"""
        )
    _seed_complaints()


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return salt.hex() + "$" + digest.hex()


def _password_matches(password: str, encoded: str) -> bool:
    try:
        salt_hex, expected = encoded.split("$", 1)
        actual = _password_hash(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def create_user(email: str, password: str) -> dict:
    email = (email or "").strip().lower()
    if not email or "@" not in email or len(password or "") < 8:
        raise ValueError("Use a valid email and a password of at least 8 characters.")
    user = {"id": "usr_" + uuid.uuid4().hex, "email": email}
    try:
        with _connect() as c:
            c.execute("INSERT INTO users(id, email, password_hash, created_at) VALUES (?,?,?,?)",
                      (user["id"], email, _password_hash(password), datetime.now().isoformat()))
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with that email already exists.") from exc
    return user


def authenticate_user(email: str, password: str) -> dict | None:
    with _connect() as c:
        row = c.execute("SELECT id, email, password_hash FROM users WHERE email=?", ((email or "").strip().lower(),)).fetchone()
    if not row or not _password_matches(password or "", row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"]}


def issue_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expiry = (datetime.now() + timedelta(days=14)).isoformat()
    with _connect() as c:
        c.execute("INSERT INTO auth_tokens(token, user_id, expires_at, created_at) VALUES (?,?,?,?)",
                  (token, user_id, expiry, datetime.now().isoformat()))
    return token


def get_user_for_token(token: str) -> dict | None:
    with _connect() as c:
        row = c.execute("""SELECT u.id, u.email FROM auth_tokens t JOIN users u ON u.id=t.user_id
                           WHERE t.token=? AND t.expires_at>?""", (token, datetime.now().isoformat())).fetchone()
    return dict(row) if row else None


def revoke_token(token: str):
    with _connect() as c:
        c.execute("DELETE FROM auth_tokens WHERE token=?", (token,))


def list_applications(session_id: str) -> list:
    with _connect() as c:
        rows = c.execute("SELECT id, service_id, status, submitted_at FROM applications WHERE session_id=? ORDER BY submitted_at DESC", (session_id,)).fetchall()
    return [dict(row) for row in rows]


def create_draft(user_id: str, service_id: str, payload: dict) -> dict:
    import json as _json
    now = datetime.now().isoformat()
    draft = {"id": "drf_" + uuid.uuid4().hex, "user_id": user_id, "service_id": service_id,
             "payload": payload, "status": "collecting", "reviewed_at": None,
             "created_at": now, "updated_at": now}
    with _connect() as c:
        c.execute("""INSERT INTO application_drafts(id,user_id,service_id,payload,status,reviewed_at,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (draft["id"], user_id, service_id, _json.dumps(payload, ensure_ascii=False), "collecting", None, now, now))
    return draft


def get_draft(draft_id: str, user_id: str) -> dict | None:
    import json as _json
    with _connect() as c:
        row = c.execute("SELECT * FROM application_drafts WHERE id=? AND user_id=?", (draft_id, user_id)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["payload"] = _json.loads(item["payload"])
    return item


def update_draft(draft_id: str, user_id: str, payload: dict, status: str | None = None, reviewed: bool = False) -> dict | None:
    import json as _json
    existing = get_draft(draft_id, user_id)
    if not existing:
        return None
    now = datetime.now().isoformat()
    next_status = status or existing["status"]
    reviewed_at = now if reviewed else existing["reviewed_at"]
    with _connect() as c:
        c.execute("""UPDATE application_drafts SET payload=?, status=?, reviewed_at=?, updated_at=?
                     WHERE id=? AND user_id=?""",
                  (_json.dumps(payload, ensure_ascii=False), next_status, reviewed_at, now, draft_id, user_id))
    return get_draft(draft_id, user_id)


def _seed_complaints():
    with _connect() as c:
        count = c.execute("SELECT COUNT(*) AS n FROM complaints").fetchone()["n"]
        if count == 0:
            for row in SEED_COMPLAINTS:
                c.execute(
                    "INSERT INTO complaints(id, status, submitted_at, department, detail, officer) VALUES (?,?,?,?,?,?)",
                    row,
                )


def get_complaint(complaint_id: str):
    with _connect() as c:
        return c.execute(
            "SELECT * FROM complaints WHERE LOWER(id)=LOWER(?)", (complaint_id,)
        ).fetchone()


def register_complaint(detail: str, department: str = ""):
    cid = "GR-" + datetime.now().strftime("%Y%m%d") + "-" + str(uuid.uuid4().int % 9000 + 1000)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _connect() as c:
        c.execute(
            "INSERT INTO complaints(id, status, submitted_at, department, detail, officer) VALUES (?,?,?,?,?,?)",
            (cid, "Registered", now, department, detail, ""),
        )
    return cid


def create_application(session_id: str, service_id: str, payload: dict, status: str = "Submitted"):
    import json as _json

    app_no = "SEV-" + datetime.now().strftime("%Y%m%d") + "-" + str(uuid.uuid4().int % 9999 + 1000)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _connect() as c:
        c.execute(
            "INSERT INTO applications(id, session_id, service_id, payload, status, submitted_at) VALUES (?,?,?,?,?,?)",
            (app_no, session_id, service_id, _json.dumps(payload, ensure_ascii=False), status, now),
        )
    return app_no


def get_application(app_no: str):
    with _connect() as c:
        row = c.execute(
            "SELECT * FROM applications WHERE LOWER(id)=LOWER(?)", (app_no,)
        ).fetchone()
    if row is None:
        return None
    item = dict(row)
    return item


def get_profile(session_id: str) -> dict:
    with _connect() as c:
        rows = c.execute(
            "SELECT key, value FROM user_profiles WHERE session_id=?", (session_id,)
        ).fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_profile(session_id: str, key: str, value: str):
    with _connect() as c:
        c.execute(
            "INSERT INTO user_profiles(session_id, key, value, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(session_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (session_id, key, str(value), datetime.now().isoformat()),
        )


def save_message(session_id: str, role: str, content: str):
    with _connect() as c:
        seq = c.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM history WHERE session_id=?",
            (session_id,),
        ).fetchone()["n"]
        c.execute(
            "INSERT INTO history(session_id, seq, role, content) VALUES (?,?,?,?)",
            (session_id, seq, role, content),
        )


def load_history(session_id: str, turns: int = 12) -> list:
    with _connect() as c:
        rows = c.execute(
            "SELECT role, content FROM history WHERE session_id=? ORDER BY seq DESC LIMIT ?",
            (session_id, turns * 2),
        ).fetchall()
    messages = [{"role": r["role"], "content": r["content"]} for r in rows]
    messages.reverse()
    return messages


def add_reminder(session_id: str, topic: str, remind_date: str):
    with _connect() as c:
        c.execute(
            "INSERT INTO reminders(session_id, topic, remind_date, created_at) VALUES (?,?,?,?)",
            (session_id, topic, remind_date, datetime.now().isoformat()),
        )


def get_reminders(session_id: str) -> list:
    with _connect() as c:
        rows = c.execute(
            "SELECT topic, remind_date FROM reminders WHERE session_id=? ORDER BY remind_date",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]
