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
- **Result:** v2 (`outputs/review/keyframes_v2_photoreal.jpg`) reads as real rural Ethiopia: dark-skinned Habesha boys, wet tsedey ground, adey abeba. Author's call on whether it "feels like a real film" pending the draft.

## E02: List-style character text makes FLUX draw panels (2026-11-25)
- **Observation (keyframes v1, FLUX.1 schnell):** 5 of 13 keyframes (s04, s05, s07, s11, s13) came out as two-panel
  "character sheet" layouts, and the boys looked light-skinned and the setting European (red-roof cottage).
- **Hypothesis:** prompts formatted as `Name: description` plus a reference-sheet habit trigger panel layouts;
  "Ethiopian" alone is too weak to set skin tone and place.
- **Change:** prompt now opens with "One single continuous cinematic frame… no panels"; characters written as plain
  sentences; descriptions say "Habesha, dark brown skin"; style block adds eucalyptus and tukul huts.
- **Result:** v2 has **0/13** panel layouts (v1: 5/13). Boys read as Ethiopian in 13/13. Model was FLUX.2 klein 4B
  with reference images, so the prompt change and the model change are confounded; a fair test would rerun v1
  prompts on klein (not done, to save daily image quota).

## E03: Reference images leak their background into every shot (2026-11-25)
- **Observation (keyframes v2, FLUX.2 klein + references):** identity is consistent (same boy, red-cap friend, chestnut
  horse with blaze in every shot), but 12/13 shots share the *same* tukul-village background as the reference
  sheets, even s08 (teff field) and s10 (jump into mud). The tall friend also reads as an adult in s04/s05.
- **Hypothesis:** FLUX.2 copies the whole reference image, not just the subject; a plain-background reference
  transfers identity without the setting. "Shaved head, tall" drifts older without an explicit age anchor.
- **Change:** reference prompt → plain light-grey studio background, no style block; style block drops tukul huts in
  favour of open fields; friends' description says "13-year-old … clearly children not adults".
- **Cost:** new references change their hashes, so all 13 keyframes regenerate (16 images of the daily allowance).
- **Result:** _fill in after keyframes v3: how many shots still share one background? does the tall friend read as a child?_
