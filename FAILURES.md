# Failures

What broke, what I tried, what fixed it (or how I worked around it). Real blockers only:
quota, memory, consistency, language, tooling. Link the `runs.jsonl` run id or error line.

Template:

## F01: _short title_
- **When / stage:**
- **Symptom:** (error text, or what looked/sounded wrong)
- **Cause:**
- **Tried:** 1. … 2. …
- **Fix / workaround:**
- **What the pipeline does now:** (e.g. new retry rule, fallback, schema check)

---

## F00: Bundled font download blocked during scaffolding (pre-story)
- **Stage:** setup (end card / Amharic text rendering)
- **Symptom:** Ethiopic title rendered as empty boxes on a Linux machine with no Ge'ez font; direct
  font downloads from GitHub/Google Fonts returned 403 from that network.
- **Fix:** took Noto Sans Ethiopic (OFL) from the `@fontsource/noto-sans-ethiopic` npm package,
  converted WOFF2 → TTF with fontTools, bundled in `assets/fonts/`; `pipeline/fonts.py` prefers
  system fonts (Nyala/Ebrima on Windows, Kefa on macOS) and falls back to the bundled one.
- **Now:** end cards and native-language SRT render identically on any machine.
