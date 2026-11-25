# Run report (generated)

Source: runs.jsonl — 334 records across 15 runs.

| Stage | Model calls | Errors | Cache hits | Fallbacks | Total latency (s) | Mean latency (s) | GPU min | List-price equiv. (USD) | Models |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| smoke | 14 | 5 | 0 | 0 | 302.6 | 21.61 | 0.0 | 0.0000 | cloudflare:@cf/black-forest-labs/flux-1-schnell, edge:am-ET-AmehaNeural, gemini:gemini-3.8-flash, gemini:gemini-3.8-flash-preview-tts, local:ffmpeg |
| narration | 19 | 0 | 72 | 0 | 194.8 | 10.25 | 0.0 | 0.0000 | edge:edge-tts |
| radio | 3 | 0 | 0 | 0 | 27.9 | 9.31 | 0.0 | 0.0000 | ffmpeg:radio-cut |
| references | 17 | 2 | 15 | 0 | 396.8 | 23.34 | 0.0 | 0.0165 | cloudflare:@cf/black-forest-labs/flux-2-klein-4b, gemini:gemini-2.5-flash-image |
| keyframes | 39 | 0 | 39 | 4 | 1247.2 | 31.98 | 0.0 | 0.0429 | cloudflare:@cf/black-forest-labs/flux-2-klein-4b |
| shots | 78 | 0 | 0 | 24 | 207.2 | 2.66 | 0.0 | 0.0000 | ffmpeg:render:kenburns |
| music | 1 | 0 | 0 | 6 | 3.3 | 3.34 | 0.0 | 0.0000 | ffmpeg:placeholder-pad |
| assemble | 3 | 0 | 0 | 0 | 148.2 | 49.40 | 0.0 | 0.0000 | ffmpeg:assemble |
| **total** | 174 | 7 | 126 | 34 | 2528.1 | | 0.0 | 0.0594 | |
