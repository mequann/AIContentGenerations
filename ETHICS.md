# Ethics: consent, labelling, licences

## 1. Consent record

**Gate:** `python -m pipeline validate` refuses to run if a storyboard character with
`real_person: true`, or a voice with `voice_is_real_person: true`, has a `consent_ref` that does
not appear in the table below. While a row is marked **PENDING**, the image stages
(`references`, `keyframes`) refuse to generate that person; narration and the radio cut,
which show no one, may run. Nothing of a real person is generated before consent is recorded.

| Ref | Person | Relation | What they agreed to (likeness / voice / story / words) | How recorded (date, medium, where stored) | Reviewed final words? |
|---|---|---|---|---|---|
| C-01 | Mequannt (the narrator, shown as a 14-year-old boy) | self | Likeness as an illustrated child, the story, the narration words | Self-consent, 2026-11-25, this repository | Yes (author) |
| C-02 | Aemro Yimer and Mikias Enyew (the two friends in the story) | childhood friends | Being part of the story and depicted as illustrated, non-photoreal boys; the story as told in `story/story.md` | Written statement from each, 2026-11-25, relayed by the author in the project chat; verbatim text in §1.1 below. Originals kept privately by the author | After the near-final cut |

### 1.1 Consent statements (verbatim, 2026-11-25)

> እኔ አእምሮ ይመር የመኳንንት አቻም ጓደኛ ስሆን የታሪኩ አካል በመሆኔ ደስ እያለኝ ሙሉ ፍቃዴን ሰጥቻለሁ።

*"I, Aemro Yimer, a friend of Mequannt Acham, am happy to be part of the story and have given my full consent."*

> እኔ ሚኪያስ እንየው የመኳንንት አቻም ጓደኛ ስሆን የታሪኩ አካል በመሆኔ ደስ እያለኝ ሙሉ ፍቃዴን ሰጥቻለሁ።

*"I, Mikias Enyew, a friend of Mequannt Acham, am happy to be part of the story and have given my full consent."*

Both friends will be shown the near-final cut before it is posted, so they see exactly how they
appear and the words used, and can ask for changes.

Notes:
- The friends' names are kept out of every prompt sent to model APIs and appear only here.
- The horse's owner is a real, unnamed person. He is shown only as a tiny, faceless distant
  figure (shot s09), is never named, and no likeness is generated.
- The friends are drawn as generic illustrated boys (not from photos), so no real face is copied.
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
