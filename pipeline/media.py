"""FFmpeg + audio helpers. Deterministic, no AI."""
from __future__ import annotations

import re
import shutil
import subprocess
import wave
from functools import lru_cache
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:  # pip-installed static build: makes a clean clone work without a system install
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # pragma: no cover
        raise FFmpegError("FFmpeg not found. Install it (Windows: `winget install Gyan.FFmpeg`) "
                          "or `pip install imageio-ffmpeg`.") from e


def run(args: list[str], cwd: Path | None = None, quiet: bool = True) -> str:
    cmd = [ffmpeg_bin(), "-hide_banner", "-y", *(["-loglevel", "error"] if quiet else []), *map(str, args)]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise FFmpegError(f"ffmpeg failed ({proc.returncode}):\n  {' '.join(cmd[:12])} ...\n{tail}")
    return proc.stderr


def probe_duration(path: Path) -> float:
    """Duration in seconds, parsed from `ffmpeg -i` (works without ffprobe)."""
    path = Path(path)
    if path.suffix.lower() == ".wav":
        try:
            return wav_duration(path)
        except wave.Error:
            pass
    proc = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not m:
        raise FFmpegError(f"cannot read duration of {path}")
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def write_pcm_wav(path: Path, pcm: bytes, rate: int = 24000, channels: int = 1, width: int = 2) -> None:
    """Gemini TTS returns raw 16-bit little-endian PCM @ 24 kHz mono."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)


def has_audio_stream(path: Path) -> bool:
    proc = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return "Audio:" in proc.stderr


def measure_loudness(path: Path) -> dict:
    """Integrated loudness / true peak via the ebur128 filter (for COSTS/EXPERIMENTS evidence)."""
    err = run(["-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], quiet=False)
    out: dict[str, float] = {}
    tail = err[err.rfind("Summary:"):] if "Summary:" in err else err
    if m := re.search(r"I:\s*(-?[\d.]+)\s*LUFS", tail):
        out["integrated_lufs"] = float(m.group(1))
    if m := re.search(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", tail):
        out["true_peak_dbfs"] = float(m.group(1)) if m.group(1) != "-inf" else float("-inf")
    return out
