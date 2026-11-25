# Architecture

## Principles

1. **One contract.** `storyboard.json` is the only thing stages share. It is validated against
   `schema/storyboard.schema.json` plus semantic rules (sequential ids, 60–90 s total, known
   characters, AI end card, consent records) before any stage runs. A bad storyboard fails in
   milliseconds, not after twenty minutes of GPU time.
2. **Stages are pure functions of their inputs.** Each stage reads only the fields it needs,
   hashes exactly those inputs, and writes `outputs/<stage>/<item>__<hash12>.<ext>`.
3. **Every model call is logged**, success or failure, to `runs.jsonl`.
4. **The film always renders.** Missing GPU outputs degrade to Ken Burns / a temp pad and are
   logged as `fallback`, never as silent success.
5. **Models are swappable.** Model ids live in `pipeline/config.py` / `.env`; providers are thin
   adapters in `pipeline/providers/`. Replacing a retired model is a config change.

## Stages and contracts

| Stage | Reads from storyboard | Upstream files | Writes | Model |
|---|---|---|---|---|
| `script` | — (story.md) | — | `storyboard.draft.json` | Gemini Flash |
| `narration` | `shots[].narration`, `voice`, `meta.language` | — | `narration/sNN__h.wav` | Gemini TTS |
| `references` | `characters[]`, `style` | — | `references/<char>_cK__h.png` | FLUX (Cloudflare) |
| `keyframes` | `shots[].keyframe`, `characters`, `style` | selected reference sheets | `keyframes/sNN_cK__h.png` | FLUX (Cloudflare) |
| `shots` | `shots[].motion`, `duration_s`, `transition`, `vertical` | keyframe, Wan clip | `shots/sNN_{16x9,9x16}__h.mp4` | Wan 2.2 (Kaggle) / FFmpeg |
| `music` | `music` | ACE-Step candidates | `music/manifest.json → score` | ACE-Step (Kaggle) / FFmpeg pad |
| `assemble` | everything above + `end_card` | all current files | `final/film_*.mp4`, SRTs, `export_report.json` | FFmpeg |

Each stage dir has a `manifest.json` saying which file is *current* for each item, with its
input hash and (for generated items) the inputs themselves, so provenance is readable
without re-running anything.

## Caching

`key = sha256(canonical_json(inputs))`. What goes into `inputs` is the design decision:

- **narration**: text, voice, style direction, language, model.
- **keyframes**: full prompt (shot prompt + character descriptions + style block), negative,
  seed, size, model, **and the file hash of each reference sheet used**. Re-picking a
  character's reference regenerates exactly the shots that character appears in.
- **Wan clips**: keyframe file hash, motion prompt, seed, frame count, resolution, model. The
  hash is the clip's filename, so an out-of-date clip from Kaggle is ignored automatically.
- **segments**: source file hash, render kind, duration, fps, size, Ken Burns params,
  vertical framing, fades. A change in shot 3's transition re-renders shots 2 and 3 only.
- **assembly** is not cached: it is deterministic, needs no model, and takes under a minute.

Candidate generation (`candidates: N`, `selected: k`) makes every candidate its own cache
entry, so changing `selected` costs nothing.

## Failure handling

| Failure | Handling |
|---|---|
| 429 rate limit / 5xx / timeout | `retry.with_retries`: exponential backoff + jitter, honours `Retry-After`/`retryDelay`, 5 attempts |
| Daily quota exhausted | `QuotaExhausted` is not retried; keyframes stop cleanly, finished shots stay cached; re-run resumes |
| Bad request (4xx) | not retried, logged with the error, stage fails loudly |
| Image model rejects seed/size | adapter retries with minimal params and logs a `note` (marks the image as not reproducible) |
| TTS returns no / too-short audio | treated as transient and retried |
| Kaggle session dies mid-batch | Kaggle script skips finished clips (atomic rename of `.part` files) |
| Wan clip missing or stale | Ken Burns fallback + `fallback` event in `runs.jsonl` |
| No ACE-Step candidates yet | deterministic placeholder pad (temp track) + `fallback` event |
| Ctrl-C | everything finished is cached; re-run continues |

## Assembly details

- Narration lines are placed at `shot.start + narration.offset_s`; picture is cut to the voice
  (`pipeline retime` suggests durations from measured TTS length).
- Score: looped/trimmed to film length, fade in 1.5 s / out 3.5 s, `volume_db`, then
  `sidechaincompress` keyed by the narration (threshold 0.02, ratio 6, attack 300 ms,
  release 1500 ms, from `config.RENDER`).
- Mix normalised with `loudnorm` to −14 LUFS integrated, −1 dBTP; measured afterwards with
  `ebur128` and written to `final/export_report.json`.
- 9:16 is framed per shot (`vertical.mode = crop | blurpad`, `focus_x`) from the source image or
  clip, not by cropping the finished 16:9 film, so vertical framing is a storyboard decision.
- Subtitles: English, ≤ 2 lines, ≤ 40 chars (16:9) or ≤ 28 chars (9:16), timed to the measured
  narration, raised above the lower UI area in vertical. Native-language SRT also exported.
- End card rendered with Pillow (Ethiopic font bundled) and added as a final segment.

## Why files, not a workflow engine

Three days, two machines (laptop + Kaggle), flaky free tiers. Plain files with hashed names
make every intermediate inspectable, make Kaggle hand-off a folder upload, and make
"regenerate one shot" demonstrable with `ls` and `tail runs.jsonl`.
