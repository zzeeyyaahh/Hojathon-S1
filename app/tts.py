import hashlib
import os

import edge_tts

_BASE = os.path.dirname(os.path.abspath(__file__))
TTS_DIR = os.path.join(_BASE, "..", "static", "tts")
VOICE = "ml-IN-SobhanaNeural"


def _cache_path(text: str) -> str:
    os.makedirs(TTS_DIR, exist_ok=True)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]
    return os.path.join(TTS_DIR, f"{h}.mp3")


def _gtts_fallback(text: str, path: str):
    from gtts import gTTS

    gTTS(text=text, lang="ml").save(path)


async def synthesize(text: str) -> str:
    text = (text or "").strip()
    if not text:
        text = "ഹലോ"
    path = _cache_path(text)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    try:
        await edge_tts.Communicate(text, VOICE).save(path)
    except Exception:
        _gtts_fallback(text, path)
    return path