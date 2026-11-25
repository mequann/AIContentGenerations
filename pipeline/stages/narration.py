"""Stage: narration — one WAV per shot via Gemini TTS (cached per line)."""
from __future__ import annotations

from ..cache import StageCache, hash_inputs
from ..config import LIST_PRICE_USD, MODELS
from ..context import Ctx, say
from ..media import wav_duration, write_pcm_wav
from ..providers import mock

STAGE = "narration"


def provider(ctx: Ctx) -> str:
    return "mock" if ctx.mock else MODELS.tts_provider


def line_inputs(ctx: Ctx, shot: dict) -> dict:
    v = ctx.sb["voice"]
    prov = provider(ctx)
    base = {"text": (shot["narration"].get("tts_text") or shot["narration"]["text"]).strip(), "language": ctx.sb["meta"]["language"]["code"],
            "provider": prov}
    if prov == "edge":  # no style prompt; voice + rate are the controls
        return {**base, "voice": MODELS.edge_voice, "rate": MODELS.edge_rate, "model": "edge-tts"}
    return {**base, "voice": v["tts_voice"], "style": shot["narration"].get("style_override") or v["style_instruction"],
            "model": "mock" if ctx.mock else MODELS.gemini_tts}


def run(ctx: Ctx) -> dict[str, float]:
    cache = StageCache(ctx.out, STAGE)
    durations: dict[str, float] = {}
    probe = line_inputs(ctx, ctx.sb["shots"][0])
    say(f"▶ narration ({probe['provider']}: {probe['model']}, voice={probe['voice']})")
    for shot in ctx.sb["shots"]:
        sid = shot["id"]
        if not shot["narration"]["text"].strip():
            cache.manifest.pop(sid, None)
            continue
        inputs = line_inputs(ctx, shot)
        key = hash_inputs(inputs)
        hit = cache.lookup(sid, key, ".wav")
        if hit and not (ctx.force and ctx.selected(sid)):
            ctx.log.cache_hit(STAGE, sid, key, str(hit))
            cache.record(sid, key, hit, duration_s=round(wav_duration(hit), 3))
            durations[sid] = wav_duration(hit)
            say(f"  ✓ {sid} cached ({durations[sid]:.1f}s)")
            continue
        if not ctx.selected(sid) and cache.current(sid):
            durations[sid] = wav_duration(cache.current(sid))
            continue
        path = cache.path_for(sid, key, ".wav")
        params = {k: v for k, v in inputs.items() if k not in ("text", "model", "provider")}
        with ctx.log.call(stage=STAGE, shot=sid, provider=inputs["provider"],
                          model=inputs["model"], params=params, input_hash=key) as rec:
            if ctx.mock:
                pcm, rate = mock.speech_pcm(inputs["text"]), 24000
            elif inputs["provider"] == "edge":
                from ..providers import edge

                edge.tts_to_wav(inputs["text"], path, voice=inputs["voice"], rate=inputs["rate"])
                pcm = None
            else:
                from ..providers import gemini

                res = gemini.tts(inputs["text"], model=MODELS.gemini_tts, voice=inputs["voice"], style=inputs["style"])
                pcm, rate = res.pcm, res.rate
                rec["model_used"] = res.model
            if pcm is not None:
                write_pcm_wav(path, pcm, rate=rate)
            dur = wav_duration(path)
            rec.update(output=str(path), audio_s=round(dur, 3),
                       cost_usd=0.0 if ctx.mock or inputs["provider"] != "gemini" else round(dur * LIST_PRICE_USD["gemini_tts_per_second_audio"], 5))
        cache.record(sid, key, path, inputs=inputs, duration_s=round(dur, 3))
        durations[sid] = dur
        say(f"  + {sid} generated ({dur:.1f}s)")

    # Fit check: narration must finish inside its shot (cut picture to the voice).
    for shot in ctx.sb["shots"]:
        d = durations.get(shot["id"])
        if d is None:
            continue
        room = shot["duration_s"] - shot["narration"]["offset_s"]
        if d > room + 0.25:
            ctx.warn(f"{shot['id']}: narration {d:.1f}s overflows shot ({room:.1f}s available) — "
                     f"lengthen duration_s to ≥ {d + shot['narration']['offset_s'] + 0.3:.1f} or shorten the line")
    total = sum(durations.values())
    say(f"  Σ narration {total:.1f}s across {len(durations)} lines")
    return durations


def fit_report(ctx: Ctx) -> list[dict]:
    """Suggested durations from measured narration (used by `pipeline retime`)."""
    cache = StageCache(ctx.out, STAGE)
    rows = []
    for shot in ctx.sb["shots"]:
        p = cache.current(shot["id"])
        d = wav_duration(p) if p else 0.0
        need = round(d + shot["narration"]["offset_s"] + 0.6, 1) if d else shot["duration_s"]
        rows.append({"shot": shot["id"], "narration_s": round(d, 2), "duration_s": shot["duration_s"],
                     "suggested_s": max(need, 3.0)})
    return rows
