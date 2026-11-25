"""Subtitle cues from narration timing: ≤2 lines × ≤40 chars, timed to the measured voice."""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _ts(t: float) -> str:
    t = max(0.0, t)
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk(text: str, max_chars: int = 40, max_lines: int = 2) -> list[str]:
    """Split text into cue blocks that each wrap to ≤ max_lines lines of ≤ max_chars."""
    text = " ".join(text.split())
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?…።])\s+", text)
    blocks: list[str] = []
    limit = max_chars * max_lines
    for sent in sentences:
        cur = ""
        for word in sent.split():
            cand = f"{cur} {word}".strip()
            if len(textwrap.wrap(cand, max_chars)) <= max_lines and len(cand) <= limit:
                cur = cand
            else:
                if cur:
                    blocks.append(cur)
                cur = word
        if cur:
            blocks.append(cur)
    return ["\n".join(textwrap.wrap(b, max_chars)) for b in blocks]


def cues_for_line(text: str, start: float, duration: float, max_chars: int = 40, max_lines: int = 2,
                  min_cue: float = 1.0) -> list[Cue]:
    blocks = chunk(text, max_chars, max_lines)
    if not blocks:
        return []
    weights = [max(len(b), 8) for b in blocks]
    total = sum(weights)
    cues, t = [], start
    for b, w in zip(blocks, weights):
        d = max(min_cue, duration * w / total)
        cues.append(Cue(round(t, 3), round(t + d, 3), b))
        t += d
    # keep inside the voiced window (min_cue may have pushed us over)
    overshoot = cues[-1].end - (start + max(duration, min_cue * len(cues)))
    if overshoot > 0:
        cues[-1].end -= overshoot
    return cues


def to_srt(cues: list[Cue]) -> str:
    out = []
    for i, c in enumerate(sorted(cues, key=lambda c: c.start), 1):
        out.append(f"{i}\n{_ts(c.start)} --> {_ts(c.end)}\n{c.text}\n")
    return "\n".join(out)
