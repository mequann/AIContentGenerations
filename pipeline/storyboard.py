"""Load, default-fill and validate storyboard.json (schema + semantic rules)."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .config import ROOT, SCHEMA_PATH


class StoryboardError(ValueError):
    pass


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _apply_defaults(sb: dict) -> dict:
    sb = copy.deepcopy(sb)
    sb["meta"].setdefault("fps", 24)
    sb["meta"].setdefault("subtitle_language", "en")
    sb["style"].setdefault("negative", "")
    sb["style"].setdefault("image_width", 1344)
    sb["style"].setdefault("image_height", 768)
    for c in sb["characters"]:
        c.setdefault("seed", 1000)
        c.setdefault("candidates", 1)
        c.setdefault("selected", 0)
    m = sb["music"]
    for k, v in {"lyrics": "[instrumental]", "seed": 42, "candidates": 3, "selected": 0, "volume_db": -6, "cues": []}.items():
        m.setdefault(k, v)
    for s in sb["shots"]:
        s.setdefault("characters", [])
        s.setdefault("transition", "cut")
        s["keyframe"].setdefault("seed", 7)
        s["keyframe"].setdefault("candidates", 1)
        s["keyframe"].setdefault("selected", 0)
        mo = s["motion"]
        mo.setdefault("prompt", "")
        mo.setdefault("seed", 11)
        mo.setdefault("trim_start_s", 0.0)
        kb = mo.setdefault("kenburns", {})
        kb.setdefault("zoom_from", 1.0)
        kb.setdefault("zoom_to", 1.12)
        kb.setdefault("pan", "none")
        s["narration"].setdefault("offset_s", 0.4)
        v = s.setdefault("vertical", {})
        v.setdefault("mode", "crop")
        v.setdefault("focus_x", 0.5)
    return sb


def semantic_errors(sb: dict, ethics_path: Path | None = None) -> list[str]:
    errs: list[str] = []
    ids = [s["id"] for s in sb["shots"]]
    if len(ids) != len(set(ids)):
        errs.append("shot ids must be unique")
    expected = [f"s{i:02d}" for i in range(1, len(ids) + 1)]
    if ids != expected:
        errs.append(f"shot ids must be sequential {expected[0]}..{expected[-1]} (got {ids})")

    char_ids = {c["id"] for c in sb["characters"]}
    for s in sb["shots"]:
        for c in s["characters"]:
            if c not in char_ids:
                errs.append(f"{s['id']}: unknown character '{c}'")
        kf = s["keyframe"]
        if kf["selected"] >= kf["candidates"]:
            errs.append(f"{s['id']}: keyframe.selected ({kf['selected']}) must be < candidates ({kf['candidates']})")
        if s["narration"]["text"].strip() and not s["narration"]["english"].strip():
            errs.append(f"{s['id']}: narration has text but no English subtitle")
    for c in sb["characters"]:
        if c["selected"] >= c["candidates"]:
            errs.append(f"character {c['id']}: selected must be < candidates")
    m = sb["music"]
    if m["selected"] >= m["candidates"]:
        errs.append("music.selected must be < music.candidates")

    total = film_duration(sb)
    if not 60.0 <= total <= 90.0:
        errs.append(f"film runs {total:.1f}s (shots + end card); must be 60–90 s")

    # Consent gate: a real person shown or voiced needs a consent record in ETHICS.md.
    ethics = ethics_path or (ROOT / "ETHICS.md")
    ethics_text = ethics.read_text(encoding="utf-8") if ethics.exists() else ""
    refs = [(f"character {c['id']}", c.get("consent_ref")) for c in sb["characters"] if c["real_person"]]
    if sb["voice"].get("voice_is_real_person"):
        refs.append(("voice", sb["voice"].get("consent_ref")))
    for who, ref in refs:
        if not ref:
            errs.append(f"{who}: real person requires consent_ref")
        elif not re.search(rf"\b{re.escape(ref)}\b", ethics_text):
            errs.append(f"{who}: consent_ref '{ref}' not found in ETHICS.md — record consent before generating")
    return errs


def pending_consent(sb: dict, ethics_path: Path | None = None) -> list[str]:
    """Consent refs whose ETHICS.md row is still marked PENDING (blocks likeness generation)."""
    ethics = ethics_path or (ROOT / "ETHICS.md")
    text = ethics.read_text(encoding="utf-8") if ethics.exists() else ""
    refs = {c.get("consent_ref") for c in sb["characters"] if c["real_person"]}
    if sb["voice"].get("voice_is_real_person"):
        refs.add(sb["voice"].get("consent_ref"))
    pending = []
    for ref in filter(None, refs):
        for line in text.splitlines():
            if re.search(rf"\|\s*{re.escape(ref)}\s*\|", line) and "PENDING" in line:
                pending.append(ref)
    return sorted(set(pending))


def load(path: Path | str, *, strict: bool = True, ethics_path: Path | None = None) -> dict:
    path = Path(path)
    if not path.exists():
        raise StoryboardError(f"{path} not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise StoryboardError(f"{path}: invalid JSON — {e}") from e
    validator = Draft202012Validator(_schema())
    schema_errs = sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path))
    if schema_errs:
        lines = [f"  - {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in schema_errs[:25]]
        raise StoryboardError(f"{path} fails schema ({len(schema_errs)} errors):\n" + "\n".join(lines))
    sb = _apply_defaults(raw)
    if strict:
        errs = semantic_errors(sb, ethics_path)
        if errs:
            raise StoryboardError(f"{path} fails semantic checks:\n" + "\n".join(f"  - {e}" for e in errs))
    return sb


def film_duration(sb: dict) -> float:
    return round(sum(s["duration_s"] for s in sb["shots"]) + sb["end_card"]["duration_s"], 3)


@dataclass(frozen=True)
class Slot:
    shot_id: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def timeline(sb: dict) -> list[Slot]:
    t, out = 0.0, []
    for s in sb["shots"]:
        out.append(Slot(s["id"], round(t, 3), round(t + s["duration_s"], 3)))
        t += s["duration_s"]
    return out


def shot_prompt(sb: dict, shot: dict) -> str:
    """Full image prompt = shot prompt + fixed character descriptions + style block.

    Drift mostly comes from re-describing things differently each time, so the
    character and style text is injected verbatim, never paraphrased.
    """
    chars = {c["id"]: c for c in sb["characters"]}
    parts = [shot["keyframe"]["prompt"].strip()]
    for cid in shot["characters"]:
        c = chars[cid]
        parts.append(f"{c['name']}: {c['description'].strip()}")
    parts.append(f"Shot size: {shot['shot_size'].replace('_', ' ')}.")
    parts.append(sb["style"]["block"].strip())
    return " ".join(parts)


def dump(sb: dict, path: Path | str) -> None:
    Path(path).write_text(json.dumps(sb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_shot(sb: dict, shot_id: str) -> dict[str, Any]:
    for s in sb["shots"]:
        if s["id"] == shot_id:
            return s
    raise StoryboardError(f"no shot {shot_id}")
