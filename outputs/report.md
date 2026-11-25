# Run report (generated)

Source: runs.jsonl — 168 records across 11 runs.

| Stage | Model calls | Errors | Cache hits | Fallbacks | Total latency (s) | Mean latency (s) | GPU min | List-price equiv. (USD) | Models |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| smoke | 14 | 5 | 0 | 0 | 302.6 | 21.61 | 0.0 | 0.0000 | cloudflare:@cf/black-forest-labs/flux-1-schnell, edge:am-ET-AmehaNeural, gemini:gemini-3.8-flash, gemini:gemini-3.8-flash-preview-tts, local:ffmpeg |
| narration | 19 | 0 | 46 | 0 | 194.8 | 10.25 | 0.0 | 0.0000 | edge:edge-tts |
| radio | 3 | 0 | 0 | 0 | 27.9 | 9.31 | 0.0 | 0.0000 | ffmpeg:radio-cut |
| references | 11 | 2 | 9 | 0 | 309.6 | 28.15 | 0.0 | 0.0099 | cloudflare:@cf/black-forest-labs/flux-2-klein-4b, gemini:gemini-2.5-flash-image |
| keyframes | 13 | 0 | 13 | 0 | 438.1 | 33.70 | 0.0 | 0.0143 | cloudflare:@cf/black-forest-labs/flux-2-klein-4b |
| shots | 26 | 0 | 0 | 8 | 60.8 | 2.34 | 0.0 | 0.0000 | ffmpeg:render:kenburns |
| music | 1 | 0 | 0 | 4 | 3.3 | 3.34 | 0.0 | 0.0000 | ffmpeg:placeholder-pad |
| assemble | 1 | 0 | 0 | 0 | 46.1 | 46.12 | 0.0 | 0.0000 | ffmpeg:assemble |
| **total** | 88 | 7 | 68 | 12 | 1383.3 | | 0.0 | 0.0242 | |
