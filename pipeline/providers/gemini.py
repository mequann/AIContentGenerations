"""Gemini API: storyboard drafting, translation and TTS (free tier, Ethiopia supported)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..config import env
from ..retry import QuotaExhausted, RetryableError, with_retries

TTS_SAMPLE_RATE = 24000


@dataclass
class TextResult:
    text: str
    in_tokens: int = 0
    out_tokens: int = 0
    model: str = ""


@dataclass
class AudioResult:
    pcm: bytes
    rate: int = TTS_SAMPLE_RATE
    model: str = ""


_CLIENT = None


def _client():
    """One long-lived client. A throwaway `genai.Client(...).models.x()` can be garbage-collected
    mid-call, which closes its HTTP session ("Cannot send a request, as the client has been closed")."""
    global _CLIENT
    if _CLIENT is None:
        key = env("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set (copy .env.example to .env)")
        from google import genai

        _CLIENT = genai.Client(api_key=key)
    return _CLIENT


def _translate_error(exc: Exception) -> Exception:
    """Map SDK errors onto our retry taxonomy."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    msg = str(exc)
    if code == 429 or "RESOURCE_EXHAUSTED" in msg:
        if re.search(r"per\s*day|PerDay|daily", msg, re.I):
            return QuotaExhausted(f"Gemini daily quota exhausted: {msg[:300]}")
        m = re.search(r"retry(?:Delay)?['\"]?:?\s*['\"]?(\d+)", msg)
        return RetryableError(f"Gemini rate limited: {msg[:200]}", retry_after=float(m.group(1)) if m else None)
    if isinstance(code, int) and code >= 500:
        return RetryableError(f"Gemini server error {code}: {msg[:200]}")
    return exc


def _fallbacks(var: str) -> list[str]:
    return [m.strip() for m in env(var).split(",") if m.strip()]


def with_model_fallback(fn, model: str, fallback_var: str, *args, **kwargs):
    """Try `model`, then each model in $fallback_var, moving on only when a model stays
    overloaded (503 / rate limit) after its own retries. Returns (result, model_used)."""
    chain = [model] + [m for m in _fallbacks(fallback_var) if m != model]
    last: Exception | None = None
    for m in chain:
        try:
            return fn(*args, model=m, **kwargs), m
        except RetryableError as e:
            last = e
            if m != chain[-1]:
                print(f"    ↪ {m} still unavailable; falling back to {chain[chain.index(m) + 1]}")
    raise last  # type: ignore[misc]


def list_models() -> list[dict]:
    out = []
    for m in _client().models.list():
        out.append({"name": m.name.removeprefix("models/"),
                    "actions": list(getattr(m, "supported_actions", None) or [])})
    return out


def generate_json(prompt: str, model: str, schema: dict | None = None, temperature: float = 0.7) -> TextResult:
    res, used = with_model_fallback(_generate_json, model, "GEMINI_TEXT_FALLBACKS", prompt,
                                    schema=schema, temperature=temperature)
    res.model = used
    return res


@with_retries(max_attempts=3)
def _generate_json(prompt: str, model: str, schema: dict | None = None, temperature: float = 0.7) -> TextResult:
    from google.genai import types

    cfg = types.GenerateContentConfig(temperature=temperature, response_mime_type="application/json")
    if schema is not None:
        cfg.response_json_schema = schema
    try:
        resp = _client().models.generate_content(model=model, contents=prompt, config=cfg)
    except Exception as e:  # noqa: BLE001
        raise _translate_error(e) from e
    text = resp.text or ""
    um = getattr(resp, "usage_metadata", None)
    return TextResult(text=text, in_tokens=getattr(um, "prompt_token_count", 0) or 0,
                      out_tokens=getattr(um, "candidates_token_count", 0) or 0)


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    return json.loads(text)


def tts(text: str, *, model: str, voice: str, style: str) -> AudioResult:
    res, used = with_model_fallback(_tts, model, "GEMINI_TTS_FALLBACKS", text, voice=voice, style=style)
    res.model = used
    return res


@with_retries(max_attempts=3)
def _tts(text: str, *, model: str, voice: str, style: str) -> AudioResult:
    """Single-speaker TTS. Style is given as a natural-language direction before the line."""
    from google.genai import types

    prompt = f"{style.strip()}\n\n{text.strip()}" if style else text
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))
        ),
    )
    try:
        resp = _client().models.generate_content(model=model, contents=prompt, config=cfg)
    except Exception as e:  # noqa: BLE001
        raise _translate_error(e) from e
    try:
        data = resp.candidates[0].content.parts[0].inline_data.data
    except (AttributeError, IndexError, TypeError) as e:
        raise RetryableError(f"TTS returned no audio (finish={getattr(resp.candidates[0], 'finish_reason', '?')})") from e
    if isinstance(data, str):  # some SDK versions return base64 text
        import base64

        data = base64.b64decode(data)
    if len(data) < TTS_SAMPLE_RATE:  # < 0.5 s of audio is a failure, not a line
        raise RetryableError(f"TTS audio suspiciously short ({len(data)} bytes)")
    return AudioResult(pcm=data)


def ping(model: str) -> TextResult:
    return generate_json('Return {"ok": true} as JSON.', model=model, temperature=0)
