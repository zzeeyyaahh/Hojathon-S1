from . import config


def transcribe(file_bytes: bytes, filename: str = "audio.webm", mime: str = "audio/webm") -> str:
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)
    resp = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=(filename, file_bytes, mime),
        language="ml",
    )
    return (resp.text or "").strip()