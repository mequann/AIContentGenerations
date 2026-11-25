"""Smoke test: call each provider once, log latency to runs.jsonl, print a table.

Tells you on day one which keys, models and quotas actually work from your network.
"""
from __future__ import annotations

import time
from pathlib import Path

from .config import MODELS, env
from .media import ffmpeg_bin, probe_duration, run as ffmpeg, write_pcm_wav
from .runlog import RunLog


def _try(log: RunLog, name: str, provider: str, model: str, fn) -> tuple[str, str, float, str]:
    t0 = time.perf_counter()
    try:
        with log.call(stage="smoke", shot=name, provider=provider, model=model) as rec:
            detail = fn()
            rec["output"] = detail
        return name, "OK", time.perf_counter() - t0, detail
    except Exception as e:  # noqa: BLE001
        return name, "FAIL", time.perf_counter() - t0, f"{type(e).__name__}: {str(e)[:140]}"


def run(log: RunLog, out: Path) -> bool:
    out.mkdir(parents=True, exist_ok=True)
    rows = []

    def ff():
        p = out / "smoke_tone.wav"
        ffmpeg(["-f", "lavfi", "-i", "sine=f=440:d=1", p])
        return f"{ffmpeg_bin()} ({probe_duration(p):.1f}s tone)"

    rows.append(_try(log, "ffmpeg", "local", "ffmpeg", ff))

    if env("GEMINI_API_KEY"):
        from .providers import gemini

        rows.append(_try(log, "gemini-text", "gemini", MODELS.gemini_text,
                         lambda: gemini.ping(MODELS.gemini_text).text.strip()[:60]))

        def tts():
            r = gemini.tts("ሰላም። እንኳን ደህና መጣችሁ።", model=MODELS.gemini_tts, voice="Kore", style="Say warmly:")
            p = out / "smoke_tts_am.wav"
            write_pcm_wav(p, r.pcm, r.rate)
            return f"{p.name} {probe_duration(p):.1f}s (listen: is the Amharic right?)"

        if MODELS.tts_provider == "gemini":
            rows.append(_try(log, "gemini-tts", "gemini", MODELS.gemini_tts, tts))
        else:
            rows.append(("gemini-tts", "SKIP", 0.0, f"TTS_PROVIDER={MODELS.tts_provider}"))
    else:
        rows.append(("gemini", "SKIP", 0.0, "GEMINI_API_KEY not set"))

    if MODELS.tts_provider == "edge":
        from .providers import edge

        def etts():
            p = out / "smoke_tts_am_edge.wav"
            edge.tts_to_wav("ሰላም። እንኳን ደህና መጣችሁ።", p, voice=MODELS.edge_voice, rate=MODELS.edge_rate)
            return f"{p.name} {probe_duration(p):.1f}s (listen: is the Amharic right?)"

        rows.append(_try(log, "edge-tts", "edge", MODELS.edge_voice, etts))

    if env("CLOUDFLARE_ACCOUNT_ID") and env("CLOUDFLARE_API_TOKEN"):
        from .providers import cloudflare as cf

        def img():
            r = cf.generate("a clay coffee pot (jebena) on a woven mat, morning light", model=MODELS.cf_image,
                            seed=1, width=1024, height=576)
            p = out / "smoke_image.png"
            p.write_bytes(cf.fit_to(r.data, 1024, 576))
            return f"{p.name} {len(r.data)//1024} KB {r.note}"

        rows.append(_try(log, "cloudflare-image", "cloudflare", MODELS.cf_image, img))
    else:
        rows.append(("cloudflare", "SKIP", 0.0, "CLOUDFLARE_* not set"))

    print(f"\n{'check':<18}{'status':<7}{'latency':>9}  detail")
    for name, status, lat, detail in rows:
        print(f"{name:<18}{status:<7}{lat:>8.2f}s  {detail}")
    print("\nKaggle (Wan 2.2 / ACE-Step) is checked inside the notebooks: see kaggle/README.md.")
    return all(r[1] != "FAIL" for r in rows)
