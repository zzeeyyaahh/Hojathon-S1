import asyncio
import hashlib
import os

import edge_tts

_BASE = os.path.dirname(os.path.abspath(__file__))
TTS_DIR = os.path.join(_BASE, "..", "static", "tts")
VOICES = {"ml": "ml-IN-SobhanaNeural", "en": "en-US-JennyNeural"}
FALLBACK_LANG = {"ml": "ml", "en": "en"}


class TTSUnavailable(Exception):
    pass


def _cache_path(text: str, lang: str) -> str:
    os.makedirs(TTS_DIR, exist_ok=True)
    h = hashlib.sha256(f"{lang}|{text}".encode("utf-8")).hexdigest()[:20]
    return os.path.join(TTS_DIR, f"{h}.mp3")


async def _gtts_fallback(text: str, path: str, lang: str):
    from gtts import gTTS

    def _do():
        gTTS(text=text, lang=FALLBACK_LANG.get(lang, "ml")).save(path)

    await asyncio.wait_for(asyncio.to_thread(_do), timeout=20)


async def synthesize(text: str, lang: str = "ml") -> str:
    lang = lang if lang in VOICES else "ml"
    text = (text or "").strip()
    if not text:
        text = "ഹലോ" if lang == "ml" else "Hello"
    path = _cache_path(text, lang)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path

    try:
        await asyncio.wait_for(edge_tts.Communicate(text, VOICES[lang]).save(path), timeout=25)
        return path
    except Exception:
        pass

    try:
        await _gtts_fallback(text, path, lang)
        return path
    except Exception:
        raise TTSUnavailable(f"TTS failed for lang={lang}")