"""Offline stand-ins so the full pipeline (and CI) runs with no keys and no GPU.

Mock outputs are clearly labelled on-frame and logged with provider="mock",
so they can never be mistaken for real generations.
"""
from __future__ import annotations

import hashlib
import io
import math
import struct

from PIL import Image, ImageDraw

from ..fonts import load_font


def _color(seed: str) -> tuple[int, int, int]:
    h = hashlib.md5(seed.encode()).digest()
    return 60 + h[0] % 120, 50 + h[1] % 110, 40 + h[2] % 100


def image(label: str, prompt: str, width: int, height: int, seed: int) -> bytes:
    a, b = _color(f"{label}{seed}"), _color(f"{prompt}{seed}")
    im = Image.new("RGB", (width, height))
    px = im.load()
    for y in range(height):
        t = y / max(1, height - 1)
        row = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        for x in range(width):
            px[x, y] = row
    d = ImageDraw.Draw(im)
    big, small = load_font(int(height * 0.12)), load_font(int(height * 0.035))
    d.text((width * 0.05, height * 0.08), label, fill=(255, 255, 255), font=big)
    d.text((width * 0.05, height * 0.25), "MOCK — not a real generation", fill=(255, 220, 120), font=small)
    words, line, y = prompt.split(), "", height * 0.34
    for w in words:
        if len(line) + len(w) > 60:
            d.text((width * 0.05, y), line, fill=(235, 235, 235), font=small)
            y += height * 0.05
            line = ""
            if y > height * 0.9:
                break
        line += w + " "
    if y <= height * 0.9:
        d.text((width * 0.05, y), line, fill=(235, 235, 235), font=small)
    # a moving-reference grid so Ken Burns motion is visible in review
    for gx in range(0, width, width // 12):
        d.line([(gx, 0), (gx, height)], fill=(255, 255, 255, 40), width=1)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def speech_pcm(text: str, rate: int = 24000, words_per_s: float = 2.3) -> bytes:
    """A syllable-like modulated tone whose length tracks the word count (≈ real narration pacing)."""
    n_words = max(1, len(text.split()))
    dur = max(1.0, n_words / words_per_s)
    n = int(dur * rate)
    out = bytearray()
    for i in range(n):
        t = i / rate
        env = 0.5 * (1 - math.cos(2 * math.pi * min(1.0, (t % 0.25) / 0.25)))  # 4 "syllables"/s
        s = 0.25 * env * (math.sin(2 * math.pi * 180 * t) + 0.5 * math.sin(2 * math.pi * 360 * t))
        out += struct.pack("<h", int(max(-1, min(1, s)) * 32767))
    return bytes(out)
