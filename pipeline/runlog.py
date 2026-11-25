"""Append-only run log: one JSON line per model call (and per cache hit).

Fields: ts, run_id, stage, shot, event, provider, model, params, seed,
latency_s, gpu_s, cost_usd (list-price equivalent), status, input_hash,
output, error.  `python -m pipeline report` aggregates this file.
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def run_id() -> str:
    return _RUN_ID


class RunLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **record: Any) -> dict:
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "run_id": _RUN_ID, **record}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        return rec

    def cache_hit(self, stage: str, shot: str | None, input_hash: str, output: str) -> None:
        self.write(stage=stage, shot=shot, event="cache_hit", input_hash=input_hash, output=output)

    @contextmanager
    def call(self, *, stage: str, shot: str | None, provider: str, model: str,
             params: dict | None = None, seed: int | None = None, input_hash: str | None = None) -> Iterator[dict]:
        """Time a model call and always log it — success or failure.

        The body may set rec["output"], rec["cost_usd"], rec["gpu_s"], rec["attempts"], rec["extra"].
        """
        rec: dict[str, Any] = {"output": None, "cost_usd": 0.0, "gpu_s": 0.0}
        t0 = time.perf_counter()
        status, error = "ok", None
        try:
            yield rec
        except BaseException as exc:  # log then re-raise
            status, error = "error", f"{type(exc).__name__}: {exc}"[:500]
            raise
        finally:
            self.write(stage=stage, shot=shot, event="model_call", provider=provider, model=model,
                       params=params or {}, seed=seed, latency_s=round(time.perf_counter() - t0, 3),
                       status=status, error=error, input_hash=input_hash, **rec)

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out
