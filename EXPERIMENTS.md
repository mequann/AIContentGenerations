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

## E01: Illustration vs photorealistic look (2026-11-25)
- **Hypothesis:** the storyteller will connect more with a photoreal film; illustration reads as "a children's book, not my memory".
- **Change:** `style.block` gouache storybook → photorealistic 35 mm cinematic; negative excludes cartoon/illustration.
- **Evidence:** author feedback on radio cut / first draft: "not seems real film" (DESIGN.md §2b).
- **Result:** _fill in after keyframes v2 (v1 sheet: `outputs/review/keyframes_v1_illustration.jpg`)._

## E02: List-style character text makes FLUX draw panels (2026-11-25)
- **Observation (keyframes v1, FLUX.1 schnell):** 5 of 13 keyframes (s04, s05, s07, s11, s13) came out as two-panel
  "character sheet" layouts, and the boys looked light-skinned and the setting European (red-roof cottage).
- **Hypothesis:** prompts formatted as `Name: description` plus a reference-sheet habit trigger panel layouts;
  "Ethiopian" alone is too weak to set skin tone and place.
- **Change:** prompt now opens with "One single continuous cinematic frame… no panels"; characters written as plain
  sentences; descriptions say "Habesha, dark brown skin"; style block adds eucalyptus and tukul huts.
- **Result:** _fill in: count of panel layouts in v2 (target 0/13); do the boys read as Ethiopian?_
