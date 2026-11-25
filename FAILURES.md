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

## F01: Gemini calls fail with "client has been closed" (smoke test, 2026-11-25)
- **Stage:** smoke → gemini-text and gemini-tts
- **Symptom:** `RuntimeError: Cannot send a request, as the client has been closed.` on the very first call, latency ~0.2–2 s.
- **Cause:** the adapter built a throwaway client per call (`genai.Client(...).models.generate_content(...)`).
  With nothing holding the `Client`, Python garbage-collected it mid-call, and its destructor closed the HTTP session.
- **Fix:** one long-lived module-level client in `pipeline/providers/gemini.py`.
- **Lesson:** SDK objects that own connections need an owner; a bug like this only appears against the real API, never with mocks.

## F02: FLUX.1 schnell on Workers AI rejects `seed` / `width` / `height` (smoke test, 2026-11-25)
- **Stage:** smoke → cloudflare-image (11.5 s)
- **Symptom:** HTTP 400 for the full payload; the adapter's fallback (prompt + steps only) succeeded and logged
  `model rejected seed/size; used minimal params (not reproducible)`.
- **Impact:** no fixed seed means no fair A/B comparison and no exact regeneration; no reference images means
  weaker character consistency across 13 shots.
- **Also seen:** prompt asked for a *jebena*; the model drew a generic clay teapot. Culture-specific objects need
  descriptive prompts ("round-bellied black clay coffee pot with a long narrow neck and spout"), not the Amharic name.
- **Next:** try FLUX.2 klein 4B (`CF_IMAGE_MODEL=@cf/black-forest-labs/flux-2-klein-4b`), which takes seed, size
  and reference images; record the result in EXPERIMENTS.md.
