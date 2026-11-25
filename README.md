# Heritage Short

A storyboard-driven pipeline that turns a family story into a 60–90 second film:
keyframes, moving shots, an original score, narration in the storyteller's language,
English subtitles, an AI end card, exported in 16:9 and 9:16, built entirely from free
hosted APIs, open weights on borrowed GPUs, and FFmpeg.

> **One command:** `python -m pipeline film` (or `make film`) regenerates the film from
> `storyboard.json`. Only shots whose inputs changed are regenerated.

```
story.md ──script──▶ storyboard.json  ◀── the contract, validated by schema/storyboard.schema.json
                         │
      ┌──────────────┬───┴──────────┬──────────────┬──────────────┐
  narration      references      keyframes        shots          music
 Gemini TTS     FLUX (CF AI)   FLUX (CF AI)    Wan 2.2 (Kaggle)  ACE-Step (Kaggle)
  per line       per char        per shot       / Ken Burns       / temp pad
      └──────────────┴──────────────┴──────┬───────┴──────────────┘
                                       assemble (FFmpeg)
                    duck · subtitles · −14 LUFS · end card · 16:9 + 9:16
```

Every model call is logged to `runs.jsonl` (model, params, seed, latency, GPU seconds,
list-price cost). Design rationale lives in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Quick start

Requirements: Python 3.10+, FFmpeg (optional: the pip package `imageio-ffmpeg` provides one).

```bash
git clone <this repo> && cd <repo>
python -m venv .venv && .venv\Scripts\activate      # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env                               # then paste your keys (cp on macOS/Linux)

python -m pipeline smoke        # calls each provider once, logs latency
python -m pipeline film         # the whole film → outputs/final/
```

No keys yet? See the whole pipeline work offline with labelled stand-in providers:

```bash
python -m pipeline --mock --draft film
```

## Keys (all free, no card)

| Service | Used for | Where |
|---|---|---|
| Gemini API | storyboard draft, translation, narration (TTS) | aistudio.google.com → API key |
| Cloudflare Workers AI | keyframes & reference sheets (FLUX) | dash.cloudflare.com → AI → Workers AI → REST API |
| Kaggle (phone-verified) | Wan 2.2 video, ACE-Step music on T4 GPUs | see [kaggle/README.md](kaggle/README.md) |

Keys live in `.env` (git-ignored). Model ids are overridable in `.env`; defaults in `pipeline/config.py`.

## The workflow

| Step | Command | Output |
|---|---|---|
| 1. Draft storyboard from your story | `python -m pipeline script` → review → `script --accept` | `storyboard.json` |
| 2. Validate contract, consent, pacing | `python -m pipeline validate` | errors / warnings |
| 3. Radio cut (user test #1) | `python -m pipeline radio` | `outputs/radio/radio_cut.mp4` |
| 4. Fit shots to the voice | `python -m pipeline retime` | suggested `duration_s` |
| 5. Character sheets + keyframes | `python -m pipeline keyframes` | `outputs/references/`, `outputs/keyframes/` |
| 6. Moving shots on Kaggle | `shots --export` → notebook → `shots --import` | `outputs/shots/wan/` |
| 7. Score on Kaggle | `music --export` → notebook → `music --import` | `outputs/music/` |
| 8. Full film | `python -m pipeline film` | `outputs/final/film_16x9.mp4`, `film_9x16.mp4`, SRTs |
| 9. Costs & latency | `python -m pipeline report` | `outputs/report.md` → COSTS.md |

Useful flags (before the command): `--draft` half-resolution, `--only s03,s07` limit
regeneration, `--force` ignore cache for the selected shots, `--mock` offline providers.
`python -m pipeline status` shows which cached file each shot is using.

### Regenerating one shot (walkthrough demo)

1. Edit `shots[2].keyframe.prompt` (or a narration line) in `storyboard.json`.
2. `python -m pipeline film`.
3. The console shows `+ s03_c0` (one new model call) and cache hits for everything else;
   `runs.jsonl` gains exactly one new `model_call` for the image stage.

## Repository layout

```
storyboard.json          the contract: shots, durations, prompts, references, narration, music cues
schema/                  JSON Schema, validated before every run
pipeline/                one module per stage + cache, retry, run log, CLI
  stages/                script · narration · keyframes (+references) · shots · music · assemble
  providers/             gemini · cloudflare · mock
kaggle/                  Wan 2.2 + ACE-Step GPU scripts and instructions
story/story.md           the story in your words (input to `script`)
tests/                   offline tests incl. a mock end-to-end film (RUN_SLOW=1)
outputs/                 generated assets, kept so every run can be inspected
runs.jsonl               one line per model call
DESIGN.md · ARCHITECTURE.md · EXPERIMENTS.md · FAILURES.md · COSTS.md · ETHICS.md
```

## What it costs

$0 on free tiers. Measured latency, GPU minutes and list-price equivalents are in
[COSTS.md](COSTS.md), generated from `runs.jsonl` with `python -m pipeline report`.

## Licences

Code: MIT. Bundled font: Noto Sans Ethiopic (SIL OFL 1.1, `assets/fonts/OFL.txt`).
Model and output licences are listed in [ETHICS.md](ETHICS.md).
# AIContentGenerations
