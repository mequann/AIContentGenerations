# Experiments

Format: **hypothesis → change → result (with evidence) → decision.** Evidence means a
`runs.jsonl` run id / input hash, a measurement, or what listeners said. Target ≈ 10 entries.

Suggested experiments this pipeline is set up for (delete once run):

- Fixed seed, two prompts → does a shorter keyframe prompt improve character consistency?
- Reference sheet passed to FLUX.2 vs description-only (FLUX.1 schnell) → consistency across 5 shots.
- Wan 2.2 at 480p/30 steps vs 720p/40 steps → latency, GPU minutes, visible difference.
- Motion prompt "camera static" vs "camera pushes in" → artefacts / warping.
- TTS style instruction variants (neutral vs "elder telling a story") → native-speaker preference.
- TTS voice A vs B for Amharic pronunciation of names → native-speaker check.
- Ducking ratio 6 vs 10, release 1500 vs 800 ms → is the voice always clear on a phone speaker?
- ACE-Step caption short vs detailed → which candidate do 3 listeners prefer under narration?
- Vertical `crop` vs `blurpad` for wide shots → which do viewers prefer on a phone?
- Open vs frontier (if access) for one shot → blind preference with ≥ 5 people.

---

## E01: _title_
- **Date:**
- **Hypothesis:**
- **Change:** (storyboard field / config / code, with commit)
- **Setup:** model, seed, params (run id: `…`)
- **Result:**
- **Decision:**
