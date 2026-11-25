"""Cross-platform font discovery (Windows, macOS, Linux) incl. Ethiopic (Ge'ez) fonts."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from .config import ROOT

LATIN = [
    Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/Library/Fonts/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    ROOT / "assets" / "fonts" / "NotoSansEthiopic-Latin-Regular.ttf",  # bundled (OFL) last-resort
]
ETHIOPIC = [
    ROOT / "assets" / "fonts" / "NotoSansEthiopic-Regular.ttf",
    Path("C:/Windows/Fonts/nyala.ttf"), Path("C:/Windows/Fonts/ebrima.ttf"),
    Path("/System/Library/Fonts/Supplemental/Kefa.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansEthiopic-Regular.ttf"),
    Path("/usr/share/fonts/truetype/abyssinica/AbyssinicaSIL-Regular.ttf"),
]


def _first(paths: list[Path]) -> Path | None:
    return next((p for p in paths if p.exists()), None)


@lru_cache(maxsize=32)
def load_font(size: int, ethiopic: bool = False):
    p = _first(ETHIOPIC if ethiopic else LATIN) or (_first(LATIN) if ethiopic else None)
    if p:
        return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def has_ethiopic(text: str) -> bool:
    return any(0x1200 <= ord(ch) <= 0x139F or 0x2D80 <= ord(ch) <= 0x2DDF for ch in text)
