# Run report (generated)

Source: runs.jsonl — 251 records across 13 runs.

| Stage | Model calls | Errors | Cache hits | Fallbacks | Total latency (s) | Mean latency (s) | GPU min | List-price equiv. (USD) | Models |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| smoke | 14 | 5 | 0 | 0 | 302.6 | 21.61 | 0.0 | 0.0000 | cloudflare:@cf/black-forest-labs/flux-1-schnell, edge:am-ET-AmehaNeural, gemini:gemini-3.8-flash, gemini:gemini-3.8-flash-preview-tts, local:ffmpeg |
| narration | 19 | 0 | 59 | 0 | 194.8 | 10.25 | 0.0 | 0.0000 | edge:edge-tts |
| radio | 3 | 0 | 0 | 0 | 27.9 | 9.31 | 0.0 | 0.0000 | ffmpeg:radio-cut |
| references | 14 | 2 | 12 | 0 | 367.7 | 26.26 | 0.0 | 0.0132 | cloudflare:@cf/black-forest-labs/flux-2-klein-4b, gemini:gemini-2.5-flash-image |
| keyframes | 26 | 0 | 26 | 2 | 955.7 | 36.76 | 0.0 | 0.0286 | cloudflare:@cf/black-forest-labs/flux-2-klein-4b |
| shots | 52 | 0 | 0 | 16 | 145.7 | 2.80 | 0.0 | 0.0000 | ffmpeg:render:kenburns |
| music | 1 | 0 | 0 | 5 | 3.3 | 3.34 | 0.0 | 0.0000 | ffmpeg:placeholder-pad |
| assemble | 2 | 0 | 0 | 0 | 88.7 | 44.33 | 0.0 | 0.0000 | ffmpeg:assemble |
| **total** | 131 | 7 | 97 | 23 | 2086.4 | | 0.0 | 0.0418 | |
