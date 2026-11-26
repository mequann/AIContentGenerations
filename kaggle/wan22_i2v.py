"""Wan 2.2 TI2V-5B image-to-video on Kaggle (2x T4) or Colab.

Usage inside a Kaggle notebook (GPU T4 x2, Internet ON):
    !pip install -q "diffusers>=0.35" transformers accelerate ftfy imageio imageio-ffmpeg
    !python /kaggle/input/<your-dataset>/wan22_i2v.py --jobs /kaggle/input/<your-dataset>/jobs.json

Input  : jobs.json + keyframes/ (made locally by `python -m pipeline shots --export`)
Output : /kaggle/working/out/<shot>__<hash>.mp4  +  results.jsonl (one line per job)
Then download /kaggle/working/out and run locally:
    python -m pipeline shots --import path/to/out

Design notes
* Resumable: finished outputs are skipped, so a session timeout only costs the clip in flight.
* Every job is logged (latency, GPU seconds, params, seed, errors) and merged into runs.jsonl on import.
* T4 has no fast bf16 → fp16 transformer + fp32 VAE, model CPU offload to fit 16 GB.
* Two GPUs: run two processes with --shard 0/2 and --shard 1/2 (one per GPU) to halve wall time.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path


def load_pipe(model_id: str, device: str):
    # pyrefly: ignore[missing-import]
    import torch
    # pyrefly: ignore[missing-import]
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline

    major = torch.cuda.get_device_capability()[0] if torch.cuda.is_available() else 0
    dtype = torch.bfloat16 if major >= 8 else torch.float16  # Ampere+ → bf16, T4 (7.5) → fp16
    vae = AutoencoderKLWan.from_pretrained(model_id, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(model_id, vae=vae, torch_dtype=dtype)
    gpu = int(device.split(":")[-1]) if ":" in device else 0
    pipe.enable_model_cpu_offload(gpu_id=gpu)
    try:
        pipe.vae.enable_tiling()
    except Exception:  # noqa: BLE001
        pass
    return pipe, str(dtype)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", default="/kaggle/working/out")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=5.0)
    ap.add_argument("--shard", default="0/1", help="i/n — process every n-th job starting at i")
    ap.add_argument("--device", default="cuda:0")
    a = ap.parse_args()

    # pyrefly: ignore[missing-import]
    import torch
    # pyrefly: ignore[missing-import]
    from diffusers.utils import export_to_video, load_image

    jobs_path = Path(a.jobs)
    jobs = json.loads(jobs_path.read_text(encoding="utf-8"))["jobs"]
    i, n = map(int, a.shard.split("/"))
    jobs = jobs[i::n]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = out / f"results_{i}.jsonl" if n > 1 else out / "results.jsonl"
    todo = [j for j in jobs if not (out / j["output_name"]).exists()]
    print(f"{len(jobs)} job(s) in shard {a.shard}, {len(todo)} to do")
    if not todo:
        return

    t_load = time.time()
    pipe, dtype = load_pipe(jobs[0]["model"], a.device)
    print(f"model loaded in {time.time() - t_load:.0f}s ({dtype})")

    for j in todo:
        params = {"steps": a.steps, "guidance": a.guidance, "num_frames": j["num_frames"],
                  "width": j["width"], "height": j["height"], "dtype": dtype, "gpu": torch.cuda.get_device_name(0)}
        t0 = time.time()
        rec = {"shot": j["shot"], "model": j["model"], "seed": j["seed"], "params": params,
               "input_hash": j["input_hash"], "n_gpus": 1}
        try:
            img_path = jobs_path.parent / j["image"]
            if not img_path.exists():
                img_path = jobs_path.parent / Path(j["image"]).name
            img = load_image(str(img_path)).resize((j["width"], j["height"]))
            gen = torch.Generator(device="cpu").manual_seed(int(j["seed"]))
            frames = pipe(image=img, prompt=j["prompt"], negative_prompt=j.get("negative") or None,
                          height=j["height"], width=j["width"], num_frames=j["num_frames"],
                          num_inference_steps=a.steps, guidance_scale=a.guidance, generator=gen).frames[0]
            tmp = out / (j["output_name"] + ".part.mp4")
            export_to_video(frames, str(tmp), fps=j["fps"])
            os.replace(tmp, out / j["output_name"])
            rec.update(status="ok", output=j["output_name"])
        except Exception as e:  # noqa: BLE001 — log and continue with the next shot
            traceback.print_exc()
            rec.update(status="error", error=f"{type(e).__name__}: {str(e)[:400]}")
            torch.cuda.empty_cache()
        rec["latency_s"] = round(time.time() - t0, 1)
        rec["gpu_s"] = rec["latency_s"]
        rec["peak_vram_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{j['shot']}: {rec['status']} in {rec['latency_s']}s (peak {rec['peak_vram_gb']} GB)")
        torch.cuda.reset_peak_memory_stats()


if __name__ == "__main__":
    main()
