"""Cloudflare Workers AI image generation (FLUX.1 schnell / FLUX.2 klein).

FLUX.1 schnell takes a JSON body; FLUX.2 models take multipart form-data and
accept reference images (input_image_0..3) — that is what we use for
character consistency when available.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

import requests

from ..config import env
from ..retry import QuotaExhausted, RetryableError, with_retries

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"


@dataclass
class ImageResult:
    data: bytes
    used_params: dict
    note: str = ""


def _endpoint(model: str) -> tuple[str, dict]:
    acct, token = env("CLOUDFLARE_ACCOUNT_ID"), env("CLOUDFLARE_API_TOKEN")
    if not acct or not token:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN not set (see .env.example)")
    return API.format(account=acct, model=model), {"Authorization": f"Bearer {token}"}


def supports_references(model: str) -> bool:
    return "flux-2" in model


def _check(resp: requests.Response) -> None:
    if resp.status_code == 429:
        body = resp.text.lower()
        if "daily" in body or "neurons" in body or "quota" in body:
            raise QuotaExhausted(f"Cloudflare daily allowance exhausted: {resp.text[:300]}")
        raise RetryableError(f"Cloudflare 429: {resp.text[:200]}", retry_after=float(resp.headers.get("Retry-After", 0)) or None)
    if resp.status_code >= 500:
        raise RetryableError(f"Cloudflare {resp.status_code}: {resp.text[:200]}")


def _decode(resp: requests.Response) -> bytes:
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("image/"):
        return resp.content
    payload = resp.json()
    if not payload.get("success", True):
        raise RuntimeError(f"Cloudflare error: {payload.get('errors')}")
    img = (payload.get("result") or {}).get("image")
    if not img:
        raise RetryableError(f"Cloudflare returned no image: {str(payload)[:200]}")
    return base64.b64decode(img)


@with_retries(max_attempts=5)
def generate(prompt: str, *, model: str, seed: int, width: int, height: int, steps: int = 4,
             references: list[Path] | None = None) -> ImageResult:
    url, headers = _endpoint(model)
    prompt = prompt[:2048]
    if supports_references(model):
        fields = {"prompt": (None, prompt), "seed": (None, str(seed)), "width": (None, str(width)),
                  "height": (None, str(height)), "steps": (None, str(steps))}
        files = dict(fields)
        for i, ref in enumerate((references or [])[:4]):
            files[f"input_image_{i}"] = (Path(ref).name, Path(ref).read_bytes(), "image/png")
        resp = requests.post(url, headers=headers, files=files, timeout=180)
        _check(resp)
        if resp.status_code >= 400:
            raise RuntimeError(f"Cloudflare {resp.status_code}: {resp.text[:300]}")
        return ImageResult(_decode(resp), {"seed": seed, "width": width, "height": height, "steps": steps,
                                           "n_refs": len(references or [])})

    # JSON models (FLUX.1 schnell). Try the full parameter set; if the model's input
    # schema rejects a field, fall back to the minimal one and record that we did.
    full = {"prompt": prompt, "steps": min(steps, 8), "seed": seed, "width": width, "height": height}
    resp = requests.post(url, headers=headers, json=full, timeout=180)
    _check(resp)
    if resp.status_code == 400:
        minimal = {"prompt": prompt, "steps": min(steps, 8)}
        resp = requests.post(url, headers=headers, json=minimal, timeout=180)
        _check(resp)
        if resp.status_code >= 400:
            raise RuntimeError(f"Cloudflare {resp.status_code}: {resp.text[:300]}")
        return ImageResult(_decode(resp), minimal, note="model rejected seed/size; used minimal params (not reproducible)")
    if resp.status_code >= 400:
        raise RuntimeError(f"Cloudflare {resp.status_code}: {resp.text[:300]}")
    return ImageResult(_decode(resp), {k: v for k, v in full.items() if k != "prompt"})


def fit_to(data: bytes, width: int, height: int) -> bytes:
    """Centre-crop + resize to the storyboard's frame so every keyframe shares one geometry."""
    from PIL import Image

    im = Image.open(io.BytesIO(data)).convert("RGB")
    target = width / height
    w, h = im.size
    if abs(w / h - target) > 0.01:
        if w / h > target:
            nw = int(h * target)
            im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w / target)
            im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    if im.size != (width, height):
        im = im.resize((width, height), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()
