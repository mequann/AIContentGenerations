"""Stage: music.

ACE-Step 1.5 runs on Kaggle/Colab (GPU). Locally we:
  * export the music job (caption, lyrics, bpm, key, seeds, duration),
  * import the generated candidates and register them under the job's input hash,
  * pick `music.selected` as the score.
Until real candidates exist, a deterministic placeholder pad (FFmpeg, no AI) is
used — that is the "temp track" for the radio cut.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from ..cache import StageCache, hash_inputs
from ..config import LIST_PRICE_USD, MODELS, ROOT
from ..context import Ctx, say
from ..media import probe_duration, run as ffmpeg
from ..storyboard import film_duration

STAGE = "music"


def job_inputs(ctx: Ctx) -> dict:
    m = ctx.sb["music"]
    return {"caption": m["caption"].strip(), "lyrics": m["lyrics"], "bpm": m.get("bpm"), "key": m.get("key"),
            "seed": m["seed"], "candidates": m["candidates"], "duration": int(film_duration(ctx.sb) + 3),
            "model": MODELS.acestep}


def job_key(ctx: Ctx) -> str:
    return hash_inputs(job_inputs(ctx))[:12]


def export_job(ctx: Ctx, dest: Path | None = None) -> Path:
    dest = Path(dest or ROOT / "kaggle" / "music_job")
    dest.mkdir(parents=True, exist_ok=True)
    job = {**job_inputs(ctx), "job_key": job_key(ctx),
           "output_names": [f"music_c{i}__{job_key(ctx)}.wav" for i in range(ctx.sb["music"]["candidates"])]}
    (dest / "music_job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    say(f"  ⇢ music job written to {dest / 'music_job.json'} — run kaggle/acestep_music.py with it")
    return dest


def import_candidates(ctx: Ctx, src: Path) -> int:
    cache = StageCache(ctx.out, STAGE)
    n = 0
    for f in sorted(Path(src).rglob("music_c*__*.*")):
        if re.fullmatch(r"music_c\d+__[0-9a-f]{12}\.(wav|mp3|flac)", f.name):
            shutil.copy2(f, cache.dir / f.name)
            n += 1
    for logf in Path(src).rglob("results.jsonl"):
        for line in filter(str.strip, logf.read_text(encoding="utf-8").splitlines()):
            r = json.loads(line)
            gpu_s = float(r.get("gpu_s", r.get("latency_s", 0)))
            ctx.log.write(stage=STAGE, shot=r.get("item"), event="model_call", provider="kaggle",
                          model=r.get("model", MODELS.acestep), params=r.get("params", {}), seed=r.get("seed"),
                          latency_s=r.get("latency_s"), gpu_s=gpu_s, status=r.get("status", "ok"),
                          error=r.get("error"), output=r.get("output"), input_hash=r.get("job_key"),
                          cost_usd=round(gpu_s / 3600 * LIST_PRICE_USD["gpu_t4_per_hour"], 4), imported_from=str(logf))
    say(f"  ⇠ imported {n} music candidate(s)")
    return n


def placeholder(path: Path, duration: float) -> None:
    """Soft, slowly breathing A-minor pad (temp track). Deterministic; contains no melody to fight the voice."""
    expr = ("0.10*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.07*t))"
            "+0.07*sin(2*PI*164.81*t)*(0.6+0.4*sin(2*PI*0.05*t+1))"
            "+0.06*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*0.09*t+2))"
            "+0.04*sin(2*PI*261.63*t)*(0.5+0.5*sin(2*PI*0.04*t+3))")
    ffmpeg(["-f", "lavfi", "-i", f"aevalsrc='{expr}|{expr}':s=48000:d={duration:.2f}",
            "-af", f"lowpass=f=1800,afade=t=in:d=2,afade=t=out:st={max(0, duration - 3):.2f}:d=3",
            "-c:a", "pcm_s16le", path])


def run(ctx: Ctx) -> Path:
    cache = StageCache(ctx.out, STAGE)
    key = job_key(ctx)
    cands = sorted(p for p in cache.dir.glob(f"music_c*__{key}.*") if p.suffix in (".wav", ".mp3", ".flac"))
    sel = ctx.sb["music"]["selected"]
    say("▶ music")
    if cands:
        pick = next((p for p in cands if p.name.startswith(f"music_c{sel}__")), None)
        if not pick:
            raise RuntimeError(f"music.selected={sel} but candidates are {[p.name for p in cands]}")
        cache.record("score", key, pick, kind="acestep", candidates=[p.name for p in cands],
                     selection_reason=ctx.sb["music"].get("selection_reason", ""))
        say(f"  ✓ score = {pick.name} (ACE-Step, {probe_duration(pick):.1f}s)")
        return pick
    dur = film_duration(ctx.sb) + 3
    pkey = hash_inputs({"placeholder": 1, "dur": round(dur, 1)})
    hit = cache.lookup("placeholder", pkey, ".wav")
    if not hit:
        hit = cache.path_for("placeholder", pkey, ".wav")
        with ctx.log.call(stage=STAGE, shot=None, provider="ffmpeg", model="placeholder-pad",
                          params={"duration": dur}, input_hash=pkey) as rec:
            placeholder(hit, dur)
            rec["output"] = str(hit)
    ctx.log.write(stage=STAGE, shot=None, event="fallback", detail=f"no ACE-Step candidates for job {key} → placeholder pad")
    cache.record("score", pkey, hit, kind="placeholder")
    say(f"  · no ACE-Step candidates for job {key} → placeholder pad ({dur:.0f}s). "
        f"Run `python -m pipeline music --export`, generate on Kaggle, then `--import`.")
    return hit
