# Design

> Written **before** generating anything; updated after each user test.

## 1. Brief

| | |
|---|---|
| **Whose story** | Mine (Mequannt), age 14, in 8th grade, with two childhood friends (consent C-01, C-02) |
| **Logline** | An eighth-grader rides a hobbled horse with its hobble rope for a bridle, gets carried into a stranger's teff, and saves himself with one well-aimed jump into the mud. |
| **Audience** | Primary: the two friends who were there, and my family. Secondary: Ethiopians who grew up walking to school across fields and now live in cities or abroad. _(proposed, confirm in test #1)_ |
| **Where they watch** | Phones, vertical, shared on WhatsApp / Telegram / TikTok; often the first seconds without sound, so subtitles are burned in |
| **Intent** | Laugh at the mischief, feel the green, muddy tsedey season again, and think "that was us". Success = the friends recognise the day and forward it. |
| **Language** | Amharic: the language we spoke that day and the language the friends will share it in. English subtitles for the wider audience. |
| **Constraints** | 60–90 s, free tiers only, ~30 GPU-h/week, 3 days |

**How might we** let two grown men relive the afternoon they nearly lost a friend to a runaway horse, and make strangers who never saw that field laugh with them?

## 2. Shot reasons

Every shot's `reason` lives in `storyboard.json`; this table is the readable copy.

| Shot | Size | Reason it exists |
|---|---|---|
| s01 | extreme wide | Establish the wide field and the long walk that frames the whole memory |
| s02 | wide | Introduce the three boys together, the bond the film is really about |
| s03 | medium | Reveal the temptation: a horse that cannot run away, front legs hobbled |
| s04 | medium close-up | The dare, and the akofada handed over, the detail the friends will remember |
| s05 | medium | The mistake that drives the story: the hobble rope tied on as a bridle |
| s06 | wide | The release: one word and the horse explodes into a gallop |
| s07 | close-up | The struggle, so the audience feels the loss of control |
| s08 | wide | Raise the stakes: someone else's teff, and friends panicking |
| s09 | extreme wide | The ticking clock: the owner coming, kept far and faceless |
| s10 | medium | Climax and choice: jump, and choose where to land |
| s11 | medium | Release the tension into laughter; the soft season saved him |
| s12 | wide | The shared escape, the image the friends will keep |
| s13 | medium (real photo) | A real photo of the three friends today: the true story behind the generated film |

Structure: setup (s01–s04) → rising action (s05–s09) → climax (s10) → release (s11–s13).
Music follows the same arc (cue list in `storyboard.json → music.cues`).

**Note:** the s13 line ("Even today, when we meet, we remember that horse and laugh") is my addition,
not part of the original telling. Test #1 should check whether it rings true or should be cut.

## 2b. Author review of radio cut v1 → changes (2026-11-25)

| Feedback (Mequannt, native speaker, storyteller) | Change |
|---|---|
| ሰጠኋቸው, ሽምጥጥ, አልገታውም, መርጬ, ወደቅሁ mispronounced | s04, s10 reworded; s06/s07 kept in his own words (ሽምጥ ሄደ, እንደ ልጓም አልገታው አለ), FAILURES F05 |
| "No image; doesn't feel like a real film" | look changed from storybook illustration to photorealistic cinematic; more real motion (Wan 2.2) |
| Include a real photo | s13 is now a real photo of the three friends today |
| አኮፋዳ is a handwoven cloth school bag (rural Amhara); የተቀየደ = tied | prompts in s02, s04, s11, s12 describe the woven cloth akofada; story notes updated |

## 3. User test #1: radio cut

- **Prototype:** `outputs/radio/radio_cut.mp4` (narration + temp pad on black, English subtitles)
- **Date / channel:** _TBD (in person / Slack / WhatsApp)_
- **People (≥ 3 from the audience):**

| # | Who (relation, age group) | What they said (verbatim where possible) | Where they reacted |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

**Insights → changes to the storyboard**

| Insight | Change (shot / field) | Commit |
|---|---|---|
| | | |

## 4. User test #2: near-final cut

- **Prototype:** `outputs/final/film_9x16.mp4` (version / commit _TBD_)

| # | Who | What they said | Where they reacted |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

**Insights → changes**

| Insight | Change | Commit |
|---|---|---|
| | | |

## 5. What I would test next
