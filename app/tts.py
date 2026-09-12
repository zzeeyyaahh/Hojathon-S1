import hashlib
import os

import edge_tts

_BASE = os.path.dirname(os.path.abspath(__file__))
TTS_DIR = os.path.join(_BASE, "..", "static", "tts")
VOICES = {"ml": "ml-IN-SobhanaNeural", "en": "en-US-JennyNeural"}
FALLBACK_LANG = {"ml": "ml", "en": "en"}


def _cache_path(text: str, lang: str) -> str:
    os.makedirs(TTS_DIR, exist_ok=True)
    h = hashlib.sha256(f"{lang}|{text}".encode("utf-8")).hexdigest()[:20]
    return os.path.join(TTS_DIR, f"{h}.mp3")


def _gtts_fallback(text: str, path: str, lang: str):
    from gtts import gTTS

    gTTS(text=text, lang=FALLBACK_LANG.get(lang, "ml")).save(path)


async def synthesize(text: str, lang: str = "ml") -> str:
    lang = lang if lang in VOICES else "ml"
    text = (text or "").strip()
    if not text:
        text = "ഹലോ" if lang == "ml" else "Hello"
    path = _cache_path(text, lang)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    try:
        await edge_tts.Communicate(text, VOICES[lang]).save(path)
    except Exception:
        _gtts_fallback(text, path, lang)
    return path