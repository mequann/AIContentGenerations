# GPU stages on Kaggle

Wan 2.2 (moving shots) and ACE-Step 1.5 (score) need a GPU. They run on Kaggle's free
T4s (~30 GPU-hours/week, phone-verified account). The local pipeline and the notebook
talk through files only, so the contract is the same whichever GPU you borrow.

```
local                                   Kaggle
─────                                   ──────
pipeline shots --export  ──jobs.json──▶  wan22_i2v.py   ──▶ out/*.mp4 + results.jsonl
pipeline shots --import  ◀───────────── download out/
pipeline music --export  ──music_job──▶  acestep_music.py ─▶ music_out/*.wav + results.jsonl
pipeline music --import  ◀───────────── download music_out/
```

File names carry the input hash (`s03__a1b2c3d4e5f6.mp4`). If you change a shot's
keyframe or motion prompt after exporting, its hash changes and the old clip is simply
ignored — the pipeline falls back to Ken Burns until a matching clip is imported.

## Wan 2.2 steps

1. `python -m pipeline keyframes` then `python -m pipeline shots --export` (default 480p; `--resolution 720p` for finals).
2. Upload `kaggle/jobs/` **and** `kaggle/wan22_i2v.py` as a new Kaggle Dataset.
3. New notebook → Accelerator **GPU T4 x2**, Internet **on**:
   ```
   !pip install -q "diffusers>=0.35" transformers accelerate ftfy imageio imageio-ffmpeg
   !cd /kaggle/input/<dataset> && \
     (python wan22_i2v.py --jobs jobs.json --shard 0/2 --device cuda:0 & \
      CUDA_VISIBLE_DEVICES=1 python wan22_i2v.py --jobs jobs.json --shard 1/2 --device cuda:0; wait)
   ```
4. Download `/kaggle/working/out` → `python -m pipeline shots --import <folder>` → `python -m pipeline film`.

Draft at 480p and ~30 steps first; note per-clip latency in EXPERIMENTS.md before spending quota on 720p.

## ACE-Step steps

1. `python -m pipeline music --export` → `kaggle/music_job/music_job.json`.
2. Upload it with `acestep_music.py`; run the cell in the script's docstring.
3. Download `music_out/` → `python -m pipeline music --import <folder>`.
4. Listen to every candidate **under the narration**, set `music.selected` and `music.selection_reason` in storyboard.json.
