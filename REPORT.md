/
Assignment
/
Details
Delivery Challenge - Week 0
Submission
Assistant
1Form
2Preview and Submit
Assignment Submission
Submit your assignment report.

Report Submission
Please provide a Google Drive link to your assignment report in PDF format
# Delivery Challenge — Week 0: Engineering Report
## AI-Content Generation: *The Heritage Short* — የተቀየደው ፈረስ (*The Hobbled Horse*)

- **Author:** Mequannt Acham · **Date:** November 26, 2026
- **Repository:** `https://github.com/mequann/AIContentGenerations`
- **Vertical Film (9:16, Main):** `<paste Google Drive / public link after final render>`
- **Horizontal Film (16:9) & Walkthrough (≤5 min):** `<paste links after final render>`
- **One-Command Reproduction:** `python -m pipeline film` (or `make film`)
- **Offline / CI Verification:** `python -m pipeline --mock --draft film` · `python -m pytest -q` (`19 passed, 1 skipped`)
- **Deliverable Specs:** 13 shots · `87.0 s` (including AI disclosure end card) · Amharic narration (`am`) · English subtitles (`en`) · `16:9` & `9:16` MP4 (`-14 LUFS`, `-1 dBTP`) · `$0` paid (free-tier APIs + Kaggle T4 GPU)

---

## 1. Executive Summary & Creative Brief

*The Hobbled Horse* (*የተቀየደው ፈረስ*) turns a true childhood memory—an eighth-grader riding a hobbled horse with only its hobble rope for a bridle, being carried into a stranger's teff field, and jumping into the muddy *tsedey* earth to save himself—into an 87-second narrated short film.

- **Primary Audience:** The two childhood friends who were there (consent `C-02`) and family.
- **Secondary Audience:** Ethiopians who grew up walking to school across rural fields and now watch short video on phones in cities or abroad.
- **Target Medium & Constraints:** Vertical (`9:16`) and horizontal (`16:9`) MP4s, designed for WhatsApp, Telegram, and TikTok where viewers often watch the first seconds muted—requiring burned-in subtitles inside the vertical safe area, `60–90 s` total runtime, and `$0` out-of-pocket cost.
- **Engineering Goal:** Build a deterministic, content-addressed, schema-validated media pipeline where `storyboard.json` is the single contract between stages, every model call is logged to `runs.jsonl`, and changing one shot regenerates only that shot.

---

## 2. System Architecture & Data Flow

### 2.1 End-to-End Architecture

```mermaid
flowchart TD
    Story["story/story.md"] -->|script stage: Gemini Flash| Draft["storyboard.draft.json"]
    Draft -->|human review + script --accept| SB["storyboard.json (Contract)"]
    Schema["schema/storyboard.schema.json"] -->|validate: JSON Schema + semantic + consent gate| SB

    SB -->|narration lines, voice, lang| Nar["Stage: narration (Gemini TTS / edge-tts)"]
    SB -->|characters[], style| Ref["Stage: references (Cloudflare FLUX.2 klein)"]
    Ref -->|selected ref sheet SHA-256| KF["Stage: keyframes (Cloudflare FLUX.2 klein)"]
    SB -->|shots[].keyframe, style| KF

    KF -->|keyframe PNG + motion prompt| ShotsExp["shots --export -> kaggle/jobs/jobs.json"]
    ShotsExp -->|Kaggle T4: wan22_i2v.py| WanOut["Wan 2.2 TI2V-5B (.mp4 + results.jsonl)"]
    WanOut -->|shots --import| Shots["Stage: shots (Wan clip OR Ken Burns fallback)"]
    KF -.->|fallback if Wan missing/stale| Shots

    SB -->|music cues, bpm, key| MusExp["music --export -> kaggle/music_job/music_job.json"]
    MusExp -->|Kaggle T4: acestep_music.py| AceOut["ACE-Step 1.5 (.wav + results.jsonl)"]
    AceOut -->|music --import| Mus["Stage: music (selected track OR placeholder pad)"]

    Nar --> Asm["Stage: assemble (FFmpeg + Pillow)"]
    Shots --> Asm
    Mus --> Asm
    SB -->|transitions, vertical focus_x, end_card| Asm

    Asm --> Out16["outputs/final/film_16x9.mp4 + SRTs"]
    Asm --> Out9["outputs/final/film_9x16.mp4 + SRTs"]
    Asm --> ExpRep["outputs/final/export_report.json"]

    Nar & Ref & KF & Shots & Mus & Asm -->|every call / hit / fallback| Log["runs.jsonl"]
    Log -->|python -m pipeline report| Rep["outputs/report.md / COSTS.md"]
```

### 2.2 Stage-by-Stage Input / Output Contracts

Every stage in `pipeline/stages/` is a pure function of its declared `storyboard.json` fields and upstream file hashes. Outputs are stored under `outputs/<stage>/<item>__<hash12>.<ext>` alongside a `manifest.json` recording the active file and exact input payload.

| Stage | Module | Exact Inputs (Hashed / Read) | Output Artifacts | Provider / Engine | Fallback / Failure Behaviour |
|---|---|---|---|---|---|
| `validate` | `pipeline/storyboard.py` | `storyboard.json`, `schema/storyboard.schema.json`, `ETHICS.md` | Pass/fail + pacing warnings | Local Python (`jsonschema`) | Fails in milliseconds before any API/GPU call if schema, duration (`60–90 s`), or consent gate fails |
| `script` | `pipeline/stages/script.py` | `story/story.md` | `storyboard.draft.json` → `storyboard.json` | Gemini Flash (`generate_json`) | Retries transient `503`/`429`; falls back across `GEMINI_TEXT_FALLBACKS` |
| `narration` | `pipeline/stages/narration.py` | `narration.tts_text` (or `.text`), `voice`, `rate`, `lang`, `provider`, `model` | `outputs/narration/sNN__<h12>.wav` + `manifest.json` | `edge-tts` (`am-ET-AmehaNeural`) / Gemini TTS | Pluggable `TTS_PROVIDER=gemini\|edge`; short/empty audio retried |
| `references` | `pipeline/stages/keyframes.py` | `characters[].description`, `seed`, `candidates`, `model` | `outputs/references/<char>_cK__<h12>.png` | Cloudflare FLUX.2 klein 4B | Blocked if `real_person: true` and consent is `PENDING` in `ETHICS.md` |
| `keyframes` | `pipeline/stages/keyframes.py` | `shot.keyframe.prompt`, `style.block`, `negative`, `seed`, `size`, `model`, **SHA-256 of reference PNGs** | `outputs/keyframes/sNN_cK__<h12>.png` | Cloudflare FLUX.2 klein 4B (or `keyframe.image` real photo) | `QuotaExhausted` stops cleanly without losing cached shots |
| `shots` | `pipeline/stages/shots.py` | Keyframe file hash, `motion`, `duration_s`, `fps`, `size`, `transition`, `vertical.mode`/`focus_x` | `kaggle/jobs/jobs.json`; `outputs/shots/sNN_{16x9,9x16}__<h12>.mp4` | Wan 2.2 TI2V-5B (Kaggle) / FFmpeg | Missing or stale Wan clip degrades to deterministic FFmpeg Ken Burns + `fallback` log |
| `music` | `pipeline/stages/music.py` | `music.cues`, `bpm`, `key`, `duration_s`, `selected` | `kaggle/music_job/music_job.json`; `outputs/music/*.wav` | ACE-Step 1.5 (Kaggle) / FFmpeg | Missing candidates degrade to deterministic ambient pad + `fallback` log |
| `assemble` | `pipeline/stages/assemble.py` | Current narration `.wav`, shot `.mp4`s, score `.wav`, `end_card`, `subtitles.py` | `outputs/final/film_{16x9,9x16}.mp4`, `subtitles_{en,am}*.srt`, `export_report.json` | FFmpeg + Pillow (`NotoSansEthiopic`) | Deterministic: `sidechaincompress` ducking + two-pass `loudnorm` (`-14 LUFS`, `-1 dBTP`) + `ebur128` verification |

### 2.3 Key Engineering Decisions

1. **Content-Addressed Caching (`pipeline/cache.py`):**
   Cache keys are computed as `sha256(canonical_json(inputs))[:12]`. Because reference sheet file hashes are included in downstream keyframe inputs—and keyframe hashes are included in Wan job filenames (`s02__719e72512a2b.mp4`)—changing one character reference or one shot prompt invalidates **only** the affected downstream items.
2. **Per-Shot Vertical Framing (`9:16`):**
   Instead of centre-cropping the finished `16:9` edit, `pipeline/stages/shots.py` renders `9:16` segments directly from each shot's source image/clip using `vertical.mode` (`crop` or `blurpad`) and `vertical.focus_x`, keeping subjects centred in vertical mobile feeds.
3. **Resilience & Observability (`pipeline/retry.py`, `pipeline/runlog.py`):**
   - `with_retries` implements exponential backoff + jitter (respecting `Retry-After` / `retryDelay`) for `429` and `5xx`, while immediately halting on `QuotaExhausted` (`limit: 0` or daily cap) so partial progress stays cached.
   - `RunLog` appends one JSON object per model call, cache hit, or fallback to `runs.jsonl` (`400` records across `16` runs), enabling `python -m pipeline report` to compute latency and cost tables directly from execution evidence.

---

## 3. Design Thinking, Audience & Storyboard Evolution

- **Narrative Arc (13 Shots, 87.0 s):**
  - *Setup (`s01–s04`):* Wide open *tsedey* field → three 13–14-year-old schoolboys → the hobbled horse → the dare and handwoven *akofada* bag passed to friends.
  - *Rising Action (`s05–s09`):* Hobble rope tied as a bridle → horse explodes into a gallop (*ሽምጥ ሄደ*) → loss of control (*እንደ ልጓም አልገታው አለ*) → charging into a stranger's teff field → owner running in the distance.
  - *Climax (`s10`):* Mid-gallop choice—aiming the jump into soft mud.
  - *Release (`s11–s13`):* Landing unhurt in laughter → shared walk home → real photo of the three friends today (`s13`, `keyframe.image`), grounding the generated film in reality.

| Shot | Dur (s) | Engine | Size | Design Reason |
|---|---:|---|---|---|
| `s01` | 6 | `kenburns` | extreme wide | Establish the wide *tsedey* field and long walk framing the memory |
| `s02` | 7 | `wan` | wide | Introduce the three boys together and the bond the film is about |
| `s03` | 6 | `wan` | medium | Reveal the temptation: a hobbled horse that cannot run away |
| `s04` | 6 | `kenburns` | medium close-up | The dare, and the woven *akofada* bag handed over |
| `s05` | 7 | `wan` | medium | The mistake: hobble rope tied on as a bridle |
| `s06` | 6 | `wan` | wide | The release: one word and the horse explodes into a gallop |
| `s07` | 6 | `wan` | close-up | The struggle, conveying loss of control |
| `s08` | 7 | `kenburns` | wide | Raise the stakes: charging into a stranger's teff, friends panicking |
| `s09` | 5 | `kenburns` | extreme wide | The ticking clock: the owner running, kept far and faceless |
| `s10` | 7 | `wan` | medium | Climax and choice: jump, and aim where to land |
| `s11` | 7 | `wan` | medium | Release tension into laughter; the soft mud saved him |
| `s12` | 6 | `wan` | wide | The shared escape—the image the friends will keep |
| `s13` | 6 | `kenburns` | medium (real photo) | Real photo of the three friends today: the true story behind the film |
- **Native-Speaker & Storyteller Review (`DESIGN.md §2b`, 2026-11-25):**
  - *Pronunciation & Wording:* `edge-tts` mispronounced labialised/palatalised Amharic forms (`ሰጠኋቸው`, `ሽምጥጥ`, `አልገታውም`, `መርጬ`, `ወደቅሁ`). Rewriting `s06`/`s07` with generic paraphrases was rejected by the storyteller as inauthentic; his exact phrasing (`ሽምጥ ሄደ`, `እንደ ልጓም አልገታው አለ`) was restored, and an optional `narration.tts_text` field was added so subtitles keep exact Amharic spelling while TTS receives phonetic text if needed.
  - *Visual Direction:* Early gouache storybook keyframes felt like "a children's book, not a real film." `style.block` was shifted to photorealistic 35 mm documentary cinema, and `s13` was updated to support a real photo (`keyframe.image`).
  - *Cultural Specificity:* Clarified *አኮፋዳ* (*akofada*) as a handwoven cloth school bag in rural Amhara prompts (`s02, s04, s11, s12`).

---

## 4. Key Experiments & Failures Log

### 4.1 Selected Experiments (`EXPERIMENTS.md`)

| ID | Hypothesis / Focus | Change | Observed Result & Decision |
|---|---|---|---|
| **E01** | Gouache illustration vs. photorealistic 35 mm cinema | Updated `style.block` & `negative` | `v2` (`outputs/review/keyframes_v2_photoreal.jpg`) reads as authentic rural Ethiopia (wet *tsedey* earth, *adey abeba*, dark-skinned Habesha boys). Adopted photorealistic look. |
| **E02** | `Name: description` list prompts cause multi-panel "character sheet" outputs in FLUX (`5/13` panels in `v1`) | Rewrote prompts to open with `"One single continuous cinematic frame… no panels"`, plain-sentence character descriptions, explicit `"Habesha, dark brown skin"` | `v2` dropped panel layouts from **`5/13` to `0/13`** and fixed skin tone/setting across **`13/13`** shots. |
| **E03** | FLUX.2 klein copies the *background* of reference sheets (`12/13` shots leaked the same tukul village; tall friend read as adult) | Switched reference prompt to plain light-grey studio background; removed tukul huts from `style.block`; added `"13-year-old … clearly children not adults"` | Regenerated references and queued `v3` keyframes to isolate identity transfer from background leakage. |

### 4.2 Real Failures & Engineering Fixes (`FAILURES.md` + Kaggle GPU Run)

| ID | Blocker | Root Cause | Engineering Fix / Workaround |
|---|---|---|---|
| **F00** | Ethiopic title rendered as empty boxes on Linux; direct font downloads returned `403` | Missing Ge'ez system font | Bundled `NotoSansEthiopic` (`SIL OFL 1.1`) in `assets/fonts/`; `pipeline/fonts.py` prefers system fonts (`Nyala`/`Ebrima`/`Kefa`) and falls back to bundled TTF. |
| **F01** | `RuntimeError: Cannot send a request, as the client has been closed` on first Gemini call | Ephemeral `genai.Client(...)` garbage-collected mid-call | Refactored `pipeline/providers/gemini.py` to hold a single module-level client. |
| **F02** | FLUX.1 schnell on Cloudflare returned HTTP `400` on `seed`/`width`/`height` | Schnell endpoint rejects seed/size parameters | Added minimal-param fallback in `cloudflare.py` (logging non-reproducibility) and upgraded default to `@cf/black-forest-labs/flux-2-klein-4b` for seed + reference support. |
| **F03** | Gemini Flash returned `503 UNAVAILABLE` across all 5 retries (`185 s`) | Single-model point of failure under load | Reduced per-model retries to `3` and added `GEMINI_TEXT_FALLBACKS` / `GEMINI_TTS_FALLBACKS` + `python -m pipeline models`. |
| **F04** | `400 Unknown name "speechConfig"` on Gemini TTS | `AQ.` API key lists 28 models but no TTS model | Made narration provider-pluggable (`TTS_PROVIDER=gemini\|edge`) with `edge-tts` (`am-ET-AmehaNeural`) as Amharic fallback; included provider + voice in cache key. |
| **F05** | `edge-tts` mispronounced labialised/palatalised Amharic (`ኋ`, `ጬ`, `ጥጥ`, `ሁ`) | TTS grapheme-to-phoneme limits | Added `narration.tts_text` override in schema/stage so subtitles stay faithful while TTS can be phonetically respelled. |
| **F06** | `429 RESOURCE_EXHAUSTED (limit: 0)` on `gemini-2.5-flash-image` | Model visible in `models` list but has `0` free-tier quota | Distinguished `limit: 0` from daily exhaustion in `QuotaExhausted` CLI output; routed images to Cloudflare Workers AI. |
| **F07** | Kaggle Wan 2.2: `keyframes/s10.png is not a valid path` & CPU RAM OOM (`Killed`) | Kaggle flattened dataset upload; parallel 2-shard run loaded two 5B models into ~30 GB CPU RAM, and `hf_xet` buffered `31.4 GB` in RAM | Patched `kaggle/wan22_i2v.py` to fall back to flat filenames; ran single-process (`--device cuda:0`) with `HF_HUB_DISABLE_XET=1` and `HF_HOME=/kaggle/temp/hf`. |

---

## 5. Measured Latency, Caching & Cost (`runs.jsonl`)

Generated directly from `runs.jsonl` (`400` records across `16` runs) via `python -m pipeline report`:

| Stage | Model Calls | Errors | Cache Hits | Fallbacks | Total Latency (s) | Mean Latency (s) | GPU Min | List-Price Equiv. (USD) | Providers / Models |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `smoke` | 14 | 5 | 0 | 0 | 302.6 | 21.61 | 0.0 | 0.0000 | `cloudflare:flux-1-schnell`, `edge:am-ET-AmehaNeural`, `gemini:gemini-3.8-flash`, `local:ffmpeg` |
| `narration` | 19 | 0 | 85 | 0 | 194.8 | 10.25 | 0.0 | 0.0000 | `edge:edge-tts` |
| `radio` | 3 | 0 | 0 | 0 | 27.9 | 9.31 | 0.0 | 0.0000 | `ffmpeg:radio-cut` |
| `references` | 17 | 2 | 18 | 0 | 396.8 | 23.34 | 0.0 | 0.0165 | `cloudflare:flux-2-klein-4b`, `gemini:gemini-2.5-flash-image` |
| `keyframes` | 39 | 0 | 52 | 5 | 1247.2 | 31.98 | 0.0 | 0.0429 | `cloudflare:flux-2-klein-4b` |
| `shots` | 104 | 0 | 0 | 32 | 352.7 | 3.39 | 0.0 | 0.0000 | `ffmpeg:render:kenburns` |
| `music` | 1 | 0 | 0 | 7 | 3.3 | 3.34 | 0.0 | 0.0000 | `ffmpeg:placeholder-pad` |
| `assemble` | 4 | 0 | 0 | 0 | 254.6 | 63.65 | 0.0 | 0.0000 | `ffmpeg:assemble` |
| **Total** | **201** | **7** | **155** | **44** | **2779.9** | — | **0.0** | **$0.0594** | **$0.00 paid (free tiers)** |

*Note: `155` cache hits avoided redundant API calls across iterations; `GPU min` updates automatically once Kaggle `results.jsonl` files are imported via `shots --import` and `music --import`.*

---

## 6. Ethics, Consent, Labelling & Licences

- **Consent Gate (`ETHICS.md` + `pipeline/storyboard.py`):** `validate` blocks image generation for any `real_person: true` character whose `consent_ref` is missing or `PENDING`.
  - `C-01`: Self-consent (Mequannt, 2026-11-25).
  - `C-02`: Written Amharic consent statements from both childhood friends (Aemro Yimer and Mikias Enyew, 2026-11-25), with scope-change confirmation scheduled on the near-final cut before public posting.
  - Real names are excluded from all model prompts; generated child depictions are text-only (no real childhood photos sent to APIs).
- **Labelling & Provenance:** Schema-enforced AI disclosure end card (`end_card.text`), MP4 `comment` metadata (`Made with AI`), SynthID/C2PA metadata preserved, and platform AI-content disclosure enabled on release.
- **Licences:** Repository code (`MIT`), `NotoSansEthiopic` (`SIL OFL 1.1`), `FLUX.2 klein 4B` (`Apache 2.0`), `Wan 2.2 TI2V-5B` (`Apache 2.0`), `ACE-Step 1.5` (`MIT`). `edge-tts` fallback is treated as non-commercial and disclosed.

---

## 7. Reflection: Suggested Practices Tested & Ceiling Work

- **Practice That Beat Instinct — JSON Contract + Radio-Cut-First:**
  Enforcing `storyboard.json` + `schema/storyboard.schema.json` before generating media, and testing the audio-only `radio_cut.mp4` first, caught Amharic TTS mispronunciations and pacing issues in seconds—before spending image or GPU quotas. Hashing reference sheets into keyframe cache keys also made character-consistency iteration surgical.
- **Practice That Needed Adaptation — Model Visibility vs. Quota & Parallel GPU Sharding:**
  1. Assuming `list_models()` meant a model was usable on the free tier failed (`F04`, `F06`); probing actual endpoints in `smoke.py` and making providers pluggable (`TTS_PROVIDER`) was essential.
  2. Running two parallel Wan 2.2 shards (`--shard 0/2` & `--shard 1/2`) on Kaggle T4 ×2 exceeded Kaggle's ~30 GB CPU RAM during model loading/downloading; switching to single-process execution with `HF_HUB_DISABLE_XET=1` and `HF_HOME=/kaggle/temp/hf` resolved the OOM.
- **Ceiling Work:**
  - Built a reusable, provider-swappable CLI (`python -m pipeline <stage>`) with `--mock` offline mode for CI, `narration.tts_text` phonetic override for low-resource Amharic TTS, cross-platform bundled Ethiopic font rendering, and per-shot `9:16` `focus_x` framing.
  - **Next:** Import the Kaggle Wan 2.2 (`8` clips) and ACE-Step 1.5 score outputs, complete User Test #1 & #2 notes in `DESIGN.md`, and run `python -m pipeline film && python -m pipeline report` for the final `720p` release.
