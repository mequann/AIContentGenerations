from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .runlog import RunLog


@dataclass
class Ctx:
    sb: dict
    storyboard_path: Path
    out: Path
    log: RunLog
    mock: bool = False
    draft: bool = False
    force: bool = False
    only: set[str] | None = None
    notes: list[str] = field(default_factory=list)

    def selected(self, shot_id: str) -> bool:
        return self.only is None or shot_id in self.only

    def warn(self, msg: str) -> None:
        self.notes.append(msg)
        print(f"  ⚠ {msg}")


def say(msg: str) -> None:
    print(msg, flush=True)
