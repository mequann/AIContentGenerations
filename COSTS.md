# Costs and latency

Everything ran on free tiers: **$0 paid**. Figures below are **measured** from `runs.jsonl`
(`python -m pipeline report` regenerates the table) plus list-price equivalents so the
numbers mean something outside a free tier.

## Free-tier limits as found (fill in on day 1)

| Service | Limit I observed | Date checked | Source |
|---|---|---|---|
| Gemini API (text) | | | AI Studio rate-limit page |
| Gemini TTS | | | |
| Cloudflare Workers AI | daily neurons ≈ … images | | dashboard |
| Kaggle GPU | … h/week, T4 x2, session ≤ 12 h | | kaggle.com/settings |

## Measured per stage (paste from `outputs/report.md`)

| Stage | Model calls | Errors | Cache hits | Total latency (s) | Mean latency (s) | GPU min | List-price equiv. (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|
| _run `python -m pipeline report`_ | | | | | | | |

## List prices used

From `pipeline/config.py → LIST_PRICE_USD`. **Verify each and record date + source.**

| Item | USD | Source / date |
|---|---:|---|
| Gemini text, per 1k output tokens | 0.0025 | |
| Gemini TTS, per second of audio | 0.0005 | |
| FLUX image on Workers AI, per image | 0.0011 | |
| T4 GPU, per hour | 0.35 | |

## Per-clip GPU cost (Wan 2.2 TI2V-5B)

| Resolution | Steps | Frames | Latency per clip (T4) | Peak VRAM | Notes |
|---|---:|---:|---:|---:|---|
| 480p | 30 | 121 | | | |
| 720p | | | | | |

## Frontier comparison (if access was granted)

| Shot | Open model (latency / cost) | Frontier model (latency / cost) | Blind preference (n) |
|---|---|---|---|
