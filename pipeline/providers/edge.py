"""Microsoft Edge read-aloud voices via the `edge-tts` package: no key, has native Amharic
(am-ET-AmehaNeural, male; am-ET-MekdesNeural, female). Used when Gemini TTS is not available
to the key. No free-text style direction: delivery is steered with rate / pitch only.
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from ..media import run as ffmpeg
from ..retry import RetryableError, with_retries


@with_retries(max_attempts=4)
def tts_to_wav(text: str, wav_path: Path, *, voice: str, rate: str = "-8%", pitch: str = "+0Hz") -> None:
    import edge_tts

    with tempfile.TemporaryDirectory() as td:
        mp3 = Path(td) / "line.mp3"

        async def _go():
            await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(mp3))

        try:
            asyncio.run(_go())
        except Exception as e:  # noqa: BLE001 — network / service hiccups are transient
            raise RetryableError(f"edge-tts failed: {type(e).__name__}: {e}") from e
        if not mp3.exists() or mp3.stat().st_size < 2000:
            raise RetryableError("edge-tts returned no audio")
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        # 24 kHz mono 16-bit, same shape as Gemini output; trim leading silence
        ffmpeg(["-i", mp3, "-af", "silenceremove=start_periods=1:start_threshold=-50dB", "-ar", "24000",
                "-ac", "1", "-c:a", "pcm_s16le", wav_path])
