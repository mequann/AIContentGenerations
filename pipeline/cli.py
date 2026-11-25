"""Command line: `python -m pipeline <command>` (see README for the full flow)."""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from . import report as report_mod
from . import smoke as smoke_mod
from .cache import StageCache
from .config import ROOT
from .context import Ctx, say
from .retry import QuotaExhausted
from .runlog import RunLog, run_id
from .storyboard import StoryboardError, film_duration, load, pending_consent


def _ctx(a: argparse.Namespace, strict: bool = True) -> Ctx:
    sb = load(a.storyboard, strict=strict)
    return Ctx(sb=sb, storyboard_path=Path(a.storyboard), out=Path(a.out), log=RunLog(Path(a.runs)),
               mock=a.mock, draft=a.draft, force=a.force, only=set(a.only.split(",")) if a.only else None)


def pacing_warnings(sb: dict) -> list[str]:
    w = []
    for s in sb["shots"]:
        words = len(s["narration"]["english"].split())
        room = s["duration_s"] - s["narration"]["offset_s"]
        if words and words / room > 2.6:
            w.append(f"{s['id']}: {words} English words in {room:.1f}s ({words / room:.1f} w/s) — likely too dense")
    return w


def cmd_validate(a):
    sb = load(a.storyboard, strict=True)
    say(f"✓ {a.storyboard} valid — {len(sb['shots'])} shots, {film_duration(sb):.1f}s incl. end card, "
        f"narration in {sb['meta']['language']['name']}")
    for w in pacing_warnings(sb):
        say(f"  ⚠ {w}")
    for ref in pending_consent(sb):
        say(f"  ⚠ consent {ref} is PENDING in ETHICS.md: images of that person are blocked until it is recorded")


def cmd_script(a):
    from .stages import script

    draft = ROOT / "storyboard.draft.json"
    if a.accept:
        script.accept(draft, Path(a.storyboard))
        return
    script.draft(Path(a.story), draft, RunLog(Path(a.runs)), lang_code=a.lang, lang_name=a.lang_name)


def cmd_narration(a):
    from .stages import narration

    narration.run(_ctx(a))


def cmd_radio(a):
    from .stages import assemble, music, narration

    ctx = _ctx(a)
    narration.run(ctx)
    music.run(ctx)
    assemble.run_radio(ctx)


def cmd_references(a):
    from .stages import keyframes

    keyframes.run_references(_ctx(a))


def cmd_keyframes(a):
    from .stages import keyframes

    ctx = _ctx(a)
    keyframes.run_references(ctx)
    keyframes.run_keyframes(ctx)


def cmd_shots(a):
    from .stages import shots

    ctx = _ctx(a)
    if a.export:
        shots.export_jobs(ctx, resolution=a.resolution)
    elif a.import_dir:
        shots.import_clips(ctx, Path(a.import_dir))
    else:
        shots.run(ctx)


def cmd_music(a):
    from .stages import music

    ctx = _ctx(a)
    if a.export:
        music.export_job(ctx)
    elif a.import_dir:
        music.import_candidates(ctx, Path(a.import_dir))
        music.run(ctx)
    else:
        music.run(ctx)


def cmd_assemble(a):
    from .stages import assemble

    assemble.run(_ctx(a))


def cmd_film(a):
    from .stages import assemble, keyframes, music, narration, shots

    t0 = time.perf_counter()
    ctx = _ctx(a)
    say(f"run {run_id()} — {len(ctx.sb['shots'])} shots, {film_duration(ctx.sb):.1f}s"
        f"{' [MOCK providers]' if ctx.mock else ''}{' [draft]' if ctx.draft else ''}")
    narration.run(ctx)
    keyframes.run_references(ctx)
    keyframes.run_keyframes(ctx)
    shots.run(ctx)
    music.run(ctx)
    assemble.run(ctx)
    report_mod.write(ctx.log, ctx.out / "report.md")
    say(f"\n✔ film done in {time.perf_counter() - t0:.1f}s — {ctx.out / 'final'}")
    if ctx.notes:
        say(f"  {len(ctx.notes)} warning(s):")
        for n in ctx.notes:
            say(f"   - {n}")


def cmd_status(a):
    ctx = _ctx(a, strict=False)
    caches = {s: StageCache(ctx.out, s) for s in ("narration", "keyframes", "shots")}
    say(f"{'shot':<5} {'dur':>5}  {'engine':<9} {'narration':<24} {'keyframe':<24} {'16x9 segment'}")
    for s in ctx.sb["shots"]:
        def name(stage, item):
            p = caches[stage].current(item)
            return p.name if p else "—"
        say(f"{s['id']:<5} {s['duration_s']:>5}  {s['motion']['engine']:<9} {name('narration', s['id']):<24} "
            f"{name('keyframes', s['id']):<24} {name('shots', s['id'] + '_16x9')}")


def cmd_retime(a):
    from .stages import narration

    for r in narration.fit_report(_ctx(a, strict=False)):
        flag = "  ← increase" if r["suggested_s"] > r["duration_s"] else ""
        say(f"{r['shot']}: narration {r['narration_s']:>5}s  duration {r['duration_s']:>5}s  suggested ≥ {r['suggested_s']}{flag}")


def cmd_smoke(a):
    ok = smoke_mod.run(RunLog(Path(a.runs)), Path(a.out) / "smoke")
    sys.exit(0 if ok else 1)


def cmd_models(a):
    """List the Gemini models this key can use — the fix when a model id has moved."""
    from .config import MODELS
    from .providers import gemini

    rows = gemini.list_models()
    tts = [r for r in rows if "tts" in r["name"]]
    flash = [r for r in rows if "flash" in r["name"] and "tts" not in r["name"] and "generateContent" in r["actions"]]
    say(f"configured: text={MODELS.gemini_text}  tts={MODELS.gemini_tts}\n")
    say("TTS models (set GEMINI_TTS_MODEL in .env):")
    for r in tts:
        say(f"  {r['name']}")
    say("\nFlash text models (GEMINI_TEXT_MODEL / GEMINI_TEXT_FALLBACKS):")
    for r in flash:
        say(f"  {r['name']}")
    shown = {r["name"] for r in tts + flash}
    say("\nOther models (name: supported actions):")
    for r in rows:
        if r["name"] not in shown:
            say(f"  {r['name']}: {', '.join(r['actions']) or '?'}")
    say(f"\n{len(rows)} models visible to this key in total.")


def cmd_report(a):
    log = RunLog(Path(a.runs))
    p = report_mod.write(log, Path(a.out) / "report.md")
    print(report_mod.build(log))
    say(f"\n→ {p}")


def cmd_clean(a):
    tmp = Path(a.out) / "_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    say(f"removed {tmp} (generated assets and runs.jsonl are kept on purpose)")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m pipeline", description="Heritage Short — storyboard-to-film pipeline")
    p.add_argument("--storyboard", default=str(ROOT / "storyboard.json"))
    p.add_argument("--out", default=str(ROOT / "outputs"))
    p.add_argument("--runs", default=str(ROOT / "runs.jsonl"))
    p.add_argument("--mock", action="store_true", help="offline stand-in providers (no keys/GPU)")
    p.add_argument("--draft", action="store_true", help="half-resolution render for fast iteration")
    p.add_argument("--force", action="store_true", help="ignore cache for selected shots")
    p.add_argument("--only", help="comma-separated shot ids to (re)generate, e.g. s03,s07")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("smoke", help="call each provider once and log latency").set_defaults(fn=cmd_smoke)
    sub.add_parser("validate", help="schema + semantic + consent checks").set_defaults(fn=cmd_validate)
    sp = sub.add_parser("script", help="draft storyboard.draft.json from a story with Gemini")
    sp.add_argument("--story", default=str(ROOT / "story" / "story.md"))
    sp.add_argument("--lang", default="am")
    sp.add_argument("--lang-name", default="Amharic")
    sp.add_argument("--accept", action="store_true", help="promote the validated draft to storyboard.json")
    sp.set_defaults(fn=cmd_script)
    sub.add_parser("narration", help="TTS one WAV per shot").set_defaults(fn=cmd_narration)
    sub.add_parser("radio", help="narration + temp score on black (user test #1)").set_defaults(fn=cmd_radio)
    sub.add_parser("references", help="character reference sheets").set_defaults(fn=cmd_references)
    sub.add_parser("keyframes", help="references + one keyframe per shot").set_defaults(fn=cmd_keyframes)
    sp = sub.add_parser("shots", help="render shot segments (or --export/--import Wan jobs)")
    sp.add_argument("--export", action="store_true")
    sp.add_argument("--import", dest="import_dir")
    sp.add_argument("--resolution", choices=["480p", "720p"], default="480p")
    sp.set_defaults(fn=cmd_shots)
    sp = sub.add_parser("music", help="select score (or --export/--import ACE-Step job)")
    sp.add_argument("--export", action="store_true")
    sp.add_argument("--import", dest="import_dir")
    sp.set_defaults(fn=cmd_music)
    sub.add_parser("assemble", help="mix, duck, subtitle, end card, export 16:9 + 9:16").set_defaults(fn=cmd_assemble)
    sub.add_parser("film", help="run every stage end to end").set_defaults(fn=cmd_film)
    sub.add_parser("status", help="what is cached for each shot").set_defaults(fn=cmd_status)
    sub.add_parser("retime", help="suggest shot durations from measured narration").set_defaults(fn=cmd_retime)
    sub.add_parser("models", help="list Gemini models available to your key").set_defaults(fn=cmd_models)
    sub.add_parser("report", help="aggregate runs.jsonl into a cost/latency table").set_defaults(fn=cmd_report)
    sub.add_parser("clean", help="remove scratch files").set_defaults(fn=cmd_clean)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except StoryboardError as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(2)
    except QuotaExhausted as e:
        msg = str(e)
        hint = ("this model has NO free-tier quota for your key (limit: 0) — switch provider/model in .env"
                if "limit: 0" in msg else "daily quota used up — re-run later; finished items are cached")
        print(f"✗ quota: {hint}\n  {msg[:300]}", file=sys.stderr)
        sys.exit(3)
    except KeyboardInterrupt:
        print("\ninterrupted — completed items are cached; re-run to resume", file=sys.stderr)
        sys.exit(130)
