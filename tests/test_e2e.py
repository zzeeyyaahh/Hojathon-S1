import sys
import time

sys.path.insert(0, r"C:\Users\hp\Desktop\hoja")

from app import agent, db

db.init_db()
sid = "e2e" 
db.init_db()


def turn(text):
    t0 = time.time()
    reply = agent.run_turn(sid, text)
    print(f"[{time.time()-t0:.1f}s] USER: {text}")
    print(f"AGENT: {reply}\n" + "-" * 70)
    return reply


turn("എനിക്ക് റേഷൻ കാർഡ് കിട്ടാൻ എന്താണ് വേണ്ടത്?")
turn("അതെ, യോഗ്യനാണോ എന്ന് പരിശോധിക്കാം. എന്റെ കുടുംബത്തിൽ 4 പേരുണ്ട്. ഞങ്ങൾക്ക് റേഷൻ കാർഡ് ഇല്ല, കുടുംബ സർവേ നടന്നിട്ടുണ്ട്")
turn("ഓക്കെ, ഫോം തുടങ്ങാം. എന്റെ പേര് അരുൺ കുമാർ, ആധാർ 123456789012, ഞാൻ എറണാകുളത്താണ്")
turn("GR-2026-1187 എന്ന പരാതി എന്ത് നിലയിലാണ്?")

print("\nPROFILE:", db.get_profile(sid))
print("HISTORY TURNS:", len(db.load_history(sid, 100)))
print("E2E DONE")