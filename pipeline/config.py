"""Central configuration: model ids, render settings and list-price table.

Everything that is likely to change week to week (model names, free-tier
limits, prices) lives here or in .env, never inside a stage script.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # .env is optional: CI and --mock runs need no secrets
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Models:
    gemini_text: str = field(default_factory=lambda: env("GEMINI_TEXT_MODEL", "gemini-3.8-flash"))
    gemini_lite: str = field(default_factory=lambda: env("GEMINI_LITE_MODEL", "gemini-3.8-flash-lite"))
    gemini_tts: str = field(default_factory=lambda: env("GEMINI_TTS_MODEL", "gemini-3.8-flash-preview-tts"))
    cf_image: str = field(default_factory=lambda: env("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell"))
    tts_provider: str = field(default_factory=lambda: env("TTS_PROVIDER", "gemini").lower())
    edge_voice: str = field(default_factory=lambda: env("EDGE_TTS_VOICE", "am-ET-AmehaNeural"))
    edge_rate: str = field(default_factory=lambda: env("EDGE_TTS_RATE", "-8%"))
    wan: str = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
    acestep: str = "ACE-Step/ACE-Step-1.5"


@dataclass(frozen=True)
class Render:
    landscape: tuple[int, int] = (1920, 1080)
    portrait: tuple[int, int] = (1080, 1920)
    draft_scale: float = 0.5               # --draft renders at half size for fast iteration
    crf: int = 20
    preset: str = "medium"
    audio_rate: int = 48000
    loudness_lufs: float = -14.0           # YouTube / Spotify reference
    true_peak_db: float = -1.0
    # Ducking (Appendix B starting point; tune by ear and log in EXPERIMENTS.md)
    duck_threshold: float = 0.02
    duck_ratio: float = 6.0
    duck_attack_ms: int = 300
    duck_release_ms: int = 1500
    subtitle_max_chars: int = 40
    subtitle_max_lines: int = 2


# List-price equivalents (USD) for COSTS.md. We pay $0 on free tiers; these
# numbers answer "what would this cost at list price?". VERIFY before quoting —
# record the date and source of each figure in COSTS.md.
LIST_PRICE_USD = {
    "gemini_text_per_1k_out_tokens": 0.0025,
    "gemini_tts_per_second_audio": 0.0005,
    "cf_image_per_image": 0.0011,     # FLUX.1 schnell ~ 512x512 @ 4 steps, neuron-based pricing
    "gpu_t4_per_hour": 0.35,          # on-demand T4 market rate used for Kaggle GPU minutes
}

MODELS = Models()
RENDER = Render()
