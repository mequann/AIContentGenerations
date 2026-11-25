"""ACE-Step 1.5 score candidates on Kaggle / Colab.

Usage (GPU notebook, Internet ON):
    !git clone https://github.com/ace-step/ACE-Step-1.5 && pip install -q -e ACE-Step-1.5
    !python acestep_music.py --job music_job.json

Input  : music_job.json (from `python -m pipeline music --export`)
Output : /kaggle/working/music_out/music_c<i>__<job_key>.wav + results.jsonl
Then locally: python -m pipeline music --import path/to/music_out

The only model-specific code is `generate()`. ACE-Step's Python API has changed
between releases — if the import below fails, check the repo README for the
current entry point, adapt `generate()`, and record what changed in FAILURES.md.
The job contract (inputs → file names → results.jsonl) stays the same.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import traceback
from pathlib import Path


def generate(caption: str, lyrics: str, duration: int, seed: int, bpm: int | None, key: str | None,
             out_path: Path) -> dict:
    """Generate one track. Returns params actually used."""
    try:  # ACE-Step 1.5 style API
        from acestep.inference import generate_music  # type: ignore

        generate_music(caption=caption, lyrics=lyrics, duration=duration, seed=seed, bpm=bpm, keyscale=key,
                       save_path=str(out_path))
        return {"api": "acestep.inference.generate_music"}
    except ImportError:
        pass
    try:  # ACE-Step v1 pipeline API
        from acestep.pipeline_ace_step import ACEStepPipeline  # type: ignore

        global _PIPE
        if "_PIPE" not in globals():
            _PIPE = ACEStepPipeline(dtype="float16")
        tags = caption + (f", {bpm} bpm" if bpm else "") + (f", {key}" if key else "")
        _PIPE(audio_duration=duration, prompt=tags, lyrics=lyrics, infer_step=60, guidance_scale=15,
              manual_seeds=[seed], save_path=str(out_path))
        return {"api": "ACEStepPipeline", "infer_step": 60, "guidance_scale": 15}
    except ImportError:
        pass
    # Last resort: the repo's CLI (prints its own help if flags differ)
    cmd = ["acestep", "--caption", caption, "--lyrics", lyrics, "--duration", str(duration),
           "--seed", str(seed), "--output", str(out_path)]
    if bpm:
        cmd += ["--bpm", str(bpm)]
    subprocess.run(cmd, check=True)
    return {"api": "cli"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--out", default="/kaggle/working/music_out")
    a = ap.parse_args()
    job = json.loads(Path(a.job).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(job["output_names"]):
        target = out / name
        if target.exists():
            continue
        seed = job["seed"] + i
        t0 = time.time()
        rec = {"item": f"music_c{i}", "model": job["model"], "seed": seed, "job_key": job["job_key"],
               "params": {"duration": job["duration"], "bpm": job.get("bpm"), "key": job.get("key")}}
        try:
            used = generate(job["caption"], job["lyrics"], job["duration"], seed, job.get("bpm"), job.get("key"), target)
            rec["params"].update(used)
            rec.update(status="ok", output=name)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            rec.update(status="error", error=f"{type(e).__name__}: {str(e)[:400]}")
        rec["latency_s"] = rec["gpu_s"] = round(time.time() - t0, 1)
        with (out / "results.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"music_c{i}: {rec['status']} in {rec['latency_s']}s")


if __name__ == "__main__":
    main()
