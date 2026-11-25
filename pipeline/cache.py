"""Content-addressed cache.

Every generated artifact is stored as  outputs/<stage>/<item>__<hash12>.<ext>
where the hash covers *exactly* the inputs that affect it (prompt, seed,
model, params, and the hashes of upstream files). Changing one shot's prompt
changes only that shot's hash, so only that shot regenerates.

A per-stage manifest.json records which file is current for each item so
downstream stages (and humans) can find it without recomputing hashes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def hash_inputs(obj: Any) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def file_hash(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


class StageCache:
    def __init__(self, out_dir: Path, stage: str):
        self.stage = stage
        self.dir = Path(out_dir) / stage
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.dir / "manifest.json"
        self.manifest: dict[str, dict] = {}
        if self.manifest_path.exists():
            try:
                self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.manifest = {}

    def path_for(self, item: str, key: str, ext: str) -> Path:
        return self.dir / f"{item}__{key[:12]}{ext}"

    def lookup(self, item: str, key: str, ext: str) -> Path | None:
        p = self.path_for(item, key, ext)
        return p if p.exists() and p.stat().st_size > 0 else None

    def record(self, item: str, key: str, path: Path, inputs: dict | None = None, **meta: Any) -> None:
        self.manifest[item] = {
            "file": Path(path).name,
            "input_hash": key,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **({"inputs": inputs} if inputs is not None else {}),
            **meta,
        }
        self.save()

    def current(self, item: str) -> Path | None:
        entry = self.manifest.get(item)
        if not entry:
            return None
        p = self.dir / entry["file"]
        return p if p.exists() else None

    def save(self) -> None:
        tmp = self.manifest_path.with_suffix(".json.part")
        tmp.write_text(json.dumps(self.manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.manifest_path)
