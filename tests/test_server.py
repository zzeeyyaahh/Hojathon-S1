import sys

sys.path.insert(0, r"C:\Users\hp\Desktop\hoja")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

r = client.get("/")
assert r.status_code == 200 and "സേവ" in r.text, r.status_code
print("index ok")

r = client.get("/api/tts", params={"text": "അത്തേ"})
assert r.status_code == 200 and r.headers["content-type"].startswith("audio"), r.status_code
print("tts ok")

r = client.post("/api/session", json={})
assert r.status_code == 200 and r.json()["session_id"]
print("session ok", r.json()["session_id"])

r = client.get("/static/app.js")
assert r.status_code == 200
print("static ok")

print("ALL SERVER TESTS PASSED")