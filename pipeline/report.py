"""Aggregate runs.jsonl into a per-stage cost/latency table (feeds COSTS.md)."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .runlog import RunLog

ORDER = ["smoke", "script", "narration", "radio", "references", "keyframes", "shots", "music", "assemble"]


def build(log: RunLog) -> str:
    recs = log.read()
    agg: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    providers: dict[str, set] = defaultdict(set)
    for r in recs:
        st = r.get("stage", "?")
        a = agg[st]
        ev = r.get("event")
        if ev == "model_call":
            a["calls"] += 1
            a["errors"] += r.get("status") == "error"
            a["latency"] += float(r.get("latency_s") or 0)
            a["gpu_s"] += float(r.get("gpu_s") or 0)
            a["cost"] += float(r.get("cost_usd") or 0)
            providers[st].add(f"{r.get('provider')}:{r.get('model')}")
        elif ev == "cache_hit":
            a["hits"] += 1
        elif ev == "fallback":
            a["fallbacks"] += 1
    runs = sorted({r.get("run_id") for r in recs if r.get("run_id")})
    lines = [
        f"Source: runs.jsonl — {len(recs)} records across {len(runs)} runs.",
        "",
        "| Stage | Model calls | Errors | Cache hits | Fallbacks | Total latency (s) | Mean latency (s) | GPU min | List-price equiv. (USD) | Models |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    tot = defaultdict(float)
    for st in sorted(agg, key=lambda s: ORDER.index(s) if s in ORDER else 99):
        a = agg[st]
        mean = a["latency"] / a["calls"] if a["calls"] else 0
        lines.append(f"| {st} | {int(a['calls'])} | {int(a['errors'])} | {int(a['hits'])} | {int(a['fallbacks'])} | "
                     f"{a['latency']:.1f} | {mean:.2f} | {a['gpu_s'] / 60:.1f} | {a['cost']:.4f} | "
                     f"{', '.join(sorted(providers[st]))} |")
        for k in ("calls", "errors", "hits", "fallbacks", "latency", "gpu_s", "cost"):
            tot[k] += a[k]
    lines.append(f"| **total** | {int(tot['calls'])} | {int(tot['errors'])} | {int(tot['hits'])} | "
                 f"{int(tot['fallbacks'])} | {tot['latency']:.1f} | | {tot['gpu_s'] / 60:.1f} | {tot['cost']:.4f} | |")
    return "\n".join(lines)


def write(log: RunLog, out: Path) -> Path:
    text = "# Run report (generated)\n\n" + build(log) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
