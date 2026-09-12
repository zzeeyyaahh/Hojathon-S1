import json
import time
from dataclasses import dataclass, field

import httpx

from . import config

_GEMINI_KEYS = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash-001"]


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list = field(default_factory=list)


def _groq_generate(messages: list, tools: list | None) -> LLMResponse:
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)
    last_err = None
    for model in config.GROQ_MODELS:
        try:
            params = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 900,
            }
            if tools:
                params["tools"] = tools
            resp = client.chat.completions.create(**params)
            msg = resp.choices[0].message
            tool_calls = []
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    tool_calls.append(
                        {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                    )
            return LLMResponse(text=msg.content or "", tool_calls=tool_calls)
        except Exception as e:  # pragma: no cover - provider errors
            last_err = e
            continue
    raise RuntimeError(f"Groq failed: {last_err}")


def _contents_from_messages(messages: list) -> list:
    """Convert OpenAI-format messages to Gemini REST `contents`, preserving
    thought_signature on functionCall parts (required by Gemini 3)."""
    contents = []
    for m in messages:
        role = m["role"]
        if role in ("system", "developer"):
            continue
        if role == "user":
            parts = []
            if m.get("content"):
                parts.append({"text": m["content"]})
            contents.append({"role": "user", "parts": parts})
        elif role == "assistant":
            parts = []
            if m.get("content"):
                parts.append({"text": m["content"]})
            for tc in m.get("tool_calls", []):
                fn = tc["function"]
                fc_part = {
                    "functionCall": {
                        "name": fn["name"],
                        "args": json.loads(fn.get("arguments") or "{}"),
                    }
                }
                if tc.get("id"):
                    fc_part["functionCall"]["id"] = tc["id"]
                if tc.get("thought_signature"):
                    fc_part["thoughtSignature"] = tc["thought_signature"]
                parts.append(fc_part)
            if parts:
                contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": m.get("name", ""),
                                "id": m.get("tool_call_id", ""),
                                "response": json.loads(m.get("content") or "{}"),
                            }
                        }
                    ],
                }
            )
    return contents


def _gemini_generate(messages: list, tools: list | None) -> LLMResponse:
    system_text = "\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = _contents_from_messages(messages)

    body: dict = {"contents": contents}
    if tools:
        body["tools"] = [
            {
                "functionDeclarations": [
                    {"name": t["function"]["name"],
                     "description": t["function"].get("description", ""),
                     "parameters": t["function"].get("parameters")}
                    for t in tools
                ]
            }
        ]
    body["generationConfig"] = {"temperature": 0.3, "maxOutputTokens": 900}
    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}

    errors = []
    for model in _GEMINI_KEYS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={config.GEMINI_API_KEY}"
        )
        # Free tier is rate-limited (429). Retry with backoff before giving up on a model.
        for attempt in (1, 2, 3):
            try:
                with httpx.Client(timeout=60) as client:
                    r = client.post(url, json=body)
                data = r.json()
                if "error" in data:
                    msg = str(data["error"].get("message", data["error"]))
                    if (r.status_code in (429, 500, 503)) and attempt < 3:
                        time.sleep(3 * attempt)
                        continue
                    raise RuntimeError(f"{model}: {msg}")
                candidate = data["candidates"][0]
                parts = candidate["content"].get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                tool_calls = []
                for p in parts:
                    if "functionCall" in p:
                        fc = p["functionCall"]
                        tool_calls.append(
                            {
                                "id": fc.get("id") or "call_gemini",
                                "name": fc["name"],
                                "arguments": json.dumps(fc.get("args", {}), ensure_ascii=False),
                                "thought_signature": p.get("thoughtSignature", ""),
                            }
                        )
                return LLMResponse(text=text, tool_calls=tool_calls)
            except httpx.HTTPError as e:
                if attempt < 3:
                    time.sleep(3 * attempt)
                    continue
                errors.append(f"{model}: {str(e)[:180]}")
    raise RuntimeError("Gemini failed on all models: " + " || ".join(errors))


def generate(messages: list, tools: list | None) -> LLMResponse:
    if not config.GROQ_API_KEY and not config.GEMINI_API_KEY:
        raise RuntimeError("No API key configured. Set GROQ_API_KEY or GEMINI_API_KEY in .env")

    if config.GROQ_API_KEY:
        try:
            return _groq_generate(messages, tools)
        except Exception as e:
            print(f"[llm] Groq failed, falling back to Gemini: {e}")
            if not config.GEMINI_API_KEY:
                raise
    if config.GEMINI_API_KEY:
        return _gemini_generate(messages, tools)
    raise RuntimeError("No working LLM provider")