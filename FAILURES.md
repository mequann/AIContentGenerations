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

## F03: Gemini text 503 "high demand" and TTS 400 "Unknown name speechConfig" (smoke test #3, 2026-11-25)
- **Text:** the key authenticates, but the configured Flash model returned 503 UNAVAILABLE on all 5 attempts
  (backoff 2→4→8→15 s; 185 s total). Retries behaved as designed; one overloaded model was a single point of failure.
  **Fix:** per-model retries cut to 3, then fall back through `GEMINI_TEXT_FALLBACKS` / `GEMINI_TTS_FALLBACKS`;
  the model actually used is logged (`model_used`).
- **TTS:** `400 INVALID_ARGUMENT: Unknown name "speechConfig"`: the request reached a model or endpoint that does
  not accept a speech config, i.e. the default TTS model id is wrong for this key.
  **Fix:** added `python -m pipeline models` to list what this key can actually call; set `GEMINI_TTS_MODEL` from it.

## F04: No Gemini TTS model available to this API key (2026-11-25)
- **Evidence:** `python -m pipeline models` lists 28 models for the key (an `AQ.`-prefixed key): Flash 2.5–3.8,
  Pro, Gemma 4, image, embedding and agent models, but **no TTS model**. The configured
  `gemini-3.8-flash-preview-tts` therefore fails with `400 Unknown name "speechConfig"`.
- **Options considered:** (1) a standard AI Studio key (`AIza…`) that may expose TTS; (2) `gemini-omni-flash-preview`
  with audio output (unverified); (3) a second TTS engine with native Amharic voices.
- **Done:** narration is now provider-pluggable (`TTS_PROVIDER=gemini|edge`). `edge` uses Microsoft neural voices
  via `edge-tts` (am-ET-AmehaNeural / am-ET-MekdesNeural), no key needed. Provider, voice and rate are part of the
  narration cache key, so switching engines regenerates every line and nothing stale is reused.
- **Trade-off:** edge voices take no natural-language style direction ("warm, amused, unhurried"); only rate and
  pitch. Compare both by ear if a Gemini TTS model becomes available (EXPERIMENTS.md).

## F05: Amharic TTS mispronounces palatalised / labialised forms (radio cut v1, 2026-11-25)
- **Voice:** edge-tts am-ET-AmehaNeural. Native-speaker check (the author) flagged: ሰጠኋቸው, ሽምጥጥ, አልገታውም,
  (ቦታ) መርጬ, ወደቅሁ. The common thread: labialised ኋ, palatalised ጬ, doubled ጥጥ, older ሁ endings.
- **Fix (v2):** rewrote those four lines in plainer spoken Amharic with the same meaning (s04, s06, s07, s10),
  e.g. ሽምጥጥ ብሎ ሄደ → እንደ ንፋስ ሮጠ, ወደቅሁ → ወደቅኩ. Added an optional `narration.tts_text` field so a line can be
  respelled for the voice while subtitles keep the correct spelling. Only the 4 changed lines regenerate.
- **Cost of the fix:** ሽምጥ ("gallop") was the storyteller's own word. **Author review of v2:** rejected the
  paraphrases for s06 and s07 as not what was said. v3 restores his wording: "ሽምጥ ሄደ" (single ጥ, which the voice
  may handle better than ሽምጥጥ) and "ገመዱ እንደ ልጓም አልገታው አለ". Authenticity of the telling outranks TTS
  convenience; if the voice still stumbles, fix with `tts_text`, not by changing the words.

## F06: Gemini image models are listed for the key but have zero free quota (2026-11-25)
- **Stage:** references (first image call), `IMAGE_PROVIDER=gemini`, model gemini-2.5-flash-image.
- **Symptom:** `429 RESOURCE_EXHAUSTED … limit: 0 … generate_content_free_tier_requests` per minute **and** per day.
- **Cause:** "listed by `models`" ≠ "usable for free". Image models are behind paid billing (as the brief warned);
  the free-tier limit is literally 0, so waiting 22 h would not help.
- **Handling:** the adapter raised `QuotaExhausted` (not retried, correct). The CLI now prints a one-line reason
  instead of a traceback and distinguishes "limit: 0" (switch provider) from "used up" (wait). Back to Cloudflare FLUX.
- **Lesson:** probe quota, not just model visibility, in the smoke test before designing around a model.
