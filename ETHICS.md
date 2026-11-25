# Ethics: consent, labelling, licences

## 1. Consent record

**Gate:** `python -m pipeline validate` refuses to run if a storyboard character with
`real_person: true`, or a voice with `voice_is_real_person: true`, has a `consent_ref` that does
not appear in the table below. Nothing of a real person is generated before consent is recorded.

| Ref | Person | Relation | What they agreed to (likeness / voice / story / words) | How recorded (date, medium, where stored) | Reviewed final words? |
|---|---|---|---|---|---|
| _C-01_ | | | | | |

Notes:
- The narration voice is a stock Gemini TTS voice unless stated above; no one's voice is cloned.
- Words placed in a real person's mouth are read back to them before release.

## 2. Labelling plan

- **In the film:** AI end card (schema-enforced: `end_card.text` must mention AI).
- **In the file:** MP4 `comment` metadata says "Made with AI"; provider watermarks /
  SynthID / C2PA are not stripped (no re-encode step removes metadata deliberately).
- **On the platform:** AI-generated / altered content disclosure switched on when posting
  (YouTube "altered or synthetic content", TikTok "AI-generated" label, Meta "AI info").
- **In the post:** text says the images, motion, voice and music were generated with AI.

## 3. Licences

| Component | Licence / terms | Commercial use of outputs | Checked |
|---|---|---|---|
| Gemini 3.x Flash / TTS (Gemini API free tier) | Google Gemini API terms; free-tier data may be used to improve products | Allowed per terms | |
| FLUX.1 schnell | Apache 2.0 | Yes | |
| FLUX.2 klein 4B | Apache 2.0 (9B variant: non-commercial) | 4B: yes | |
| Wan 2.2 TI2V-5B | Apache 2.0 | Yes | |
| ACE-Step 1.5 | MIT; trained on licensed / royalty-free / synthetic data | Yes | |
| FFmpeg | LGPL/GPL (tool, not distributed) | n/a | |
| Noto Sans Ethiopic (bundled) | SIL OFL 1.1 | Yes | ✓ |
| This repository's code | MIT | n/a | ✓ |

## 4. Style and privacy

- Prompts describe qualities (medium, palette, light), never a living artist's name.
- Private family details (full names, addresses, health) are kept out of prompts sent to
  free-tier endpoints that may train on inputs.
