"""Stage: script — turn a story (story/story.md) into a draft storyboard with Gemini.

Writes storyboard.draft.json (never overwrites storyboard.json). A human reviews,
edits, and promotes it with `python -m pipeline script --accept`.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..cache import hash_inputs
from ..config import LIST_PRICE_USD, MODELS, ROOT, SCHEMA_PATH
from ..context import say
from ..runlog import RunLog
from ..storyboard import StoryboardError, dump, load

GUIDE = """You are a documentary director and storyboard artist making a 60–90 second vertical-first short film
about a family story. Write a storyboard as JSON that validates against the JSON Schema below.

Rules:
- 8 to 12 shots. Sum of shot durations + end_card.duration_s must be between 62 and 85 seconds.
- Shot ids s01, s02, ... in order. Every shot has a one-sentence `reason` (why the film needs it).
- Narration `text` is written in {lang_name} ({lang_code}), for the ear: short sentences, concrete images.
  `english` is a faithful English subtitle of the same line. Budget ≈ 2.2 English words per second of shot.
- Some shots may have no narration (text and english both "") to let the picture and music breathe.
- keyframe.prompt describes subject, place, light and composition of ONE still image. Do not repeat the
  character description or the style — those are injected automatically. Never ask for written text in the image.
- motion.prompt describes ONLY motion and camera (e.g. "she slowly lifts the cup, camera pushes in gently").
  Use engine "wan" for shots where movement matters, "kenburns" for calm establishing/insert shots.
- Vary shot sizes: open wide to establish place, medium for action, close-ups for feeling.
- style.block: a fixed visual style (medium, palette, light, texture). Describe qualities; never name a living artist.
- music.caption: ACE-Step caption with style, mood, instruments, texture (no tempo or key in the caption).
  Use lyrics "[instrumental]". Put bpm and key in their own fields.
- characters: one entry per recurring person with a precise, fixed visual description (age, face, hair,
  clothing, distinctive objects). Set real_person true for real family members and consent_ref "C-01", "C-02", ...
- end_card.text must say the film was made with AI.
- meta.audience and meta.intent: use what the author says below; otherwise propose them.

Author's notes and story:
---
{story}
---

JSON Schema:
{schema}
"""


def draft(story_path: Path, out_path: Path, log: RunLog, lang_code: str = "am", lang_name: str = "Amharic",
          model: str | None = None) -> Path:
    from ..providers import gemini

    story = Path(story_path).read_text(encoding="utf-8")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt = GUIDE.format(story=story.strip(), schema=json.dumps(schema), lang_code=lang_code, lang_name=lang_name)
    model = model or MODELS.gemini_text
    key = hash_inputs({"prompt": prompt, "model": model})
    say(f"▶ script ({model}) — drafting storyboard from {story_path}")
    with log.call(stage="script", shot=None, provider="gemini", model=model,
                  params={"story_chars": len(story), "language": lang_code}, input_hash=key) as rec:
        res = gemini.generate_json(prompt, model=model, temperature=0.8)
        sb = gemini.parse_json(res.text)
        sb.setdefault("version", "1.0")
        dump(sb, out_path)
        rec.update(output=str(out_path), in_tokens=res.in_tokens, out_tokens=res.out_tokens,
                   cost_usd=round(res.out_tokens / 1000 * LIST_PRICE_USD["gemini_text_per_1k_out_tokens"], 5))
    try:
        load(out_path, strict=False)
        say(f"  ✓ {out_path} passes the schema. Review it, then: python -m pipeline script --accept")
    except StoryboardError as e:
        say(f"  ⚠ draft written but needs fixes:\n{e}")
    return out_path


def accept(draft_path: Path, target: Path) -> None:
    load(draft_path, strict=True)  # must fully pass before it becomes the contract
    if target.exists():
        backup = target.with_name(f"{target.stem}.prev.json")
        backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        say(f"  previous storyboard saved to {backup.name}")
    target.write_text(Path(draft_path).read_text(encoding="utf-8"), encoding="utf-8")
    say(f"  ✓ {draft_path.name} → {target.name}")


DEFAULT_STORY = ROOT / "story" / "story.md"
