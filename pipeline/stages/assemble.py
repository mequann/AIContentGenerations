"""Stage: assembly (pure FFmpeg, deterministic).

  narration lines placed at shot start + offset
  score looped/trimmed to the film, faded, ducked under the voice (sidechaincompress)
  mix normalised to −14 LUFS / −1 dBTP
  shot segments + AI end card concatenated per aspect
  English subtitles burned in (safe-area margins for 9:16), SRT sidecars exported
Outputs: outputs/final/film_16x9.mp4, film_9x16.mp4, subtitles_en.srt, subtitles_<lang>.srt
Also builds the radio cut (narration + temp score on black) for the first user test.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw

from ..cache import StageCache
from ..config import RENDER, ROOT
from ..context import Ctx, say
from ..fonts import has_ethiopic, load_font
from ..media import measure_loudness, probe_duration, run as ffmpeg
from ..storyboard import film_duration, timeline
from ..subtitles import Cue, cues_for_line, to_srt
from . import shots as shots_stage

PORTRAIT_SUB_CHARS = 28
FONTS_DIR = ROOT / "assets" / "fonts"
SUB_STYLE = {
    "16x9": "FontName=Arial,FontSize=15,PrimaryColour=&H00FFFFFF,OutlineColour=&H90000000,BorderStyle=1,"
            "Outline=1.2,Shadow=0.5,MarginV=16,MarginL=30,MarginR=30",
    "9x16": "FontName=Arial,FontSize=10,PrimaryColour=&H00FFFFFF,OutlineColour=&H90000000,BorderStyle=1,"
            "Outline=0.9,Shadow=0.4,MarginV=62,MarginL=14,MarginR=14",
}


# ----------------------------------------------------------------------------- audio

def narration_events(ctx: Ctx) -> list[tuple[str, Path, float, float]]:
    """(shot_id, wav, start_s, duration_s) for every voiced shot."""
    cache = StageCache(ctx.out, "narration")
    slots = {s.shot_id: s for s in timeline(ctx.sb)}
    ev = []
    for shot in ctx.sb["shots"]:
        if not shot["narration"]["text"].strip():
            continue
        p = cache.current(shot["id"])
        if not p:
            raise RuntimeError(f"{shot['id']}: narration missing — run `python -m pipeline narration`")
        ev.append((shot["id"], p, slots[shot["id"]].start + shot["narration"]["offset_s"], probe_duration(p)))
    return ev


def build_mix(ctx: Ctx, music: Path, out_wav: Path, total: float) -> Path:
    ev = narration_events(ctx)
    r = RENDER
    args: list = []
    for _, wav, _, _ in ev:
        args += ["-i", wav]
    args += ["-stream_loop", "-1", "-i", music]
    k = len(ev)
    parts = []
    for i, (_, _, start, _) in enumerate(ev):
        ms = int(round(start * 1000))
        parts.append(f"[{i}:a]aresample={r.audio_rate},aformat=sample_fmts=fltp:channel_layouts=stereo,"
                     f"adelay={ms}|{ms}[n{i}]")
    if k:
        parts.append("".join(f"[n{i}]" for i in range(k)) +
                     f"amix=inputs={k}:normalize=0:duration=longest,apad=whole_dur={total:.3f},"
                     f"atrim=0:{total:.3f},asplit=2[nv][nsc]")
    vol = ctx.sb["music"]["volume_db"]
    parts.append(f"[{k}:a]aresample={r.audio_rate},aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol}dB,afade=t=in:d=1.5,"
                 f"afade=t=out:st={max(0, total - 3.5):.3f}:d=3.5[mus]")
    if k:
        parts.append(f"[mus][nsc]sidechaincompress=threshold={r.duck_threshold}:ratio={r.duck_ratio}:"
                     f"attack={r.duck_attack_ms}:release={r.duck_release_ms}:makeup=1[duck]")
        parts.append("[nv][duck]amix=inputs=2:normalize=0:duration=first[pre]")
    else:
        parts.append("[mus]anull[pre]")
    parts.append(f"[pre]loudnorm=I={r.loudness_lufs}:TP={r.true_peak_db}:LRA=11,aresample={r.audio_rate}[mix]")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg([*args, "-filter_complex", ";".join(parts), "-map", "[mix]", "-t", f"{total:.3f}",
            "-c:a", "pcm_s16le", out_wav])
    return out_wav


def build_subtitles(ctx: Ctx, out_dir: Path, max_chars: int | None = None, tag: str = "") -> dict[str, Path]:
    """Cues are re-chunked per aspect: a 9:16 frame fits ~28 chars/line at a readable size."""
    max_chars = max_chars or RENDER.subtitle_max_chars
    ev = {sid: (start, dur) for sid, _, start, dur in narration_events(ctx)}
    en: list[Cue] = []
    native: list[Cue] = []
    for shot in ctx.sb["shots"]:
        if shot["id"] not in ev:
            continue
        start, dur = ev[shot["id"]]
        en += cues_for_line(shot["narration"]["english"], start, dur, max_chars, RENDER.subtitle_max_lines)
        native += cues_for_line(shot["narration"]["text"], start, dur, max_chars, RENDER.subtitle_max_lines)
    out_dir.mkdir(parents=True, exist_ok=True)
    lang = ctx.sb["meta"]["language"]["code"]
    p_en, p_nat = out_dir / f"subtitles_en{tag}.srt", out_dir / f"subtitles_{lang}{tag}.srt"
    p_en.write_text(to_srt(en), encoding="utf-8")
    if lang != "en":
        p_nat.write_text(to_srt(native), encoding="utf-8")
    return {"en": p_en, lang: p_nat}


# ----------------------------------------------------------------------------- end card

def end_card_png(ctx: Ctx, W: int, H: int, path: Path) -> Path:
    ec, meta = ctx.sb["end_card"], ctx.sb["meta"]
    im = Image.new("RGB", (W, H), (18, 15, 13))
    d = ImageDraw.Draw(im)
    unit = min(W, H)
    y = H * (0.34 if H > W else 0.28)

    def centered(text: str, size: int, color, gap: float = 1.5):
        nonlocal y
        font = load_font(size, ethiopic=has_ethiopic(text))
        for line in _wrap(d, text, font, W * 0.84):
            tw = d.textlength(line, font=font)
            d.text(((W - tw) / 2, y), line, font=font, fill=color)
            y += size * gap

    if meta.get("title_native"):
        centered(meta["title_native"], int(unit * 0.085), (240, 220, 190), 1.4)
    centered(meta["title"], int(unit * 0.06), (225, 225, 225), 1.9)
    d.line([(W * 0.35, y), (W * 0.65, y)], fill=(200, 150, 90), width=max(2, unit // 300))
    y += unit * 0.05
    centered(ec["text"], int(unit * 0.045), (245, 245, 245), 1.5)
    if ec.get("subtext"):
        y += unit * 0.01
        centered(ec["subtext"], int(unit * 0.03), (170, 170, 170), 1.5)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG")
    return path


def _wrap(d: ImageDraw.ImageDraw, text: str, font, max_w: float) -> list[str]:
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            cand = f"{cur} {w}".strip()
            if d.textlength(cand, font=font) <= max_w or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------------- video

def concat(segments: list[Path], out: Path) -> Path:
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segments), encoding="utf-8")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    lst.unlink(missing_ok=True)
    return out


def mux_with_subs(video: Path, audio: Path, srt: Path, aspect: str, out: Path) -> Path:
    # Run inside the SRT's folder and pass a bare filename: avoids FFmpeg filter-path
    # escaping problems with Windows drive letters ("C\:/...").
    style = SUB_STYLE[aspect]
    fontsdir = os.path.relpath(FONTS_DIR, srt.parent).replace("\\", "/")
    vf = f"subtitles={srt.name}:charenc=UTF-8:fontsdir='{fontsdir}':force_style='{style}'"
    ffmpeg(["-i", video.resolve(), "-i", audio.resolve(), "-map", "0:v", "-map", "1:a", "-vf", vf,
            "-c:v", "libx264", "-preset", RENDER.preset, "-crf", str(RENDER.crf), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", str(RENDER.audio_rate), "-shortest",
            "-movflags", "+faststart", "-metadata", "comment=Made with AI (see ETHICS.md)", out.resolve()],
           cwd=srt.parent)
    return out


def run(ctx: Ctx) -> dict[str, Path]:
    say("▶ assemble")
    fps = ctx.sb["meta"]["fps"]
    total = film_duration(ctx.sb)
    final = ctx.out / "final"
    tmp = ctx.out / "_tmp"
    final.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)

    music = StageCache(ctx.out, "music").current("score")
    if not music:
        raise RuntimeError("no score — run `python -m pipeline music`")
    mix = build_mix(ctx, music, tmp / "mix.wav", total)
    subs = {"16x9": build_subtitles(ctx, final),
            "9x16": build_subtitles(ctx, final, max_chars=PORTRAIT_SUB_CHARS, tag="_vertical")}
    shots_cache = StageCache(ctx.out, "shots")
    suffix = "_draft" if ctx.draft else ""
    results: dict[str, Path] = {}
    with ctx.log.call(stage="assemble", shot=None, provider="ffmpeg", model="assemble",
                      params={"draft": ctx.draft, "duration": total}) as rec:
        for aspect, (W, H) in shots_stage.sizes(ctx).items():
            segs = []
            for s in ctx.sb["shots"]:
                p = shots_cache.current(f"{s['id']}_{aspect}")
                if not p:
                    raise RuntimeError(f"{s['id']}_{aspect}: segment missing — run `python -m pipeline shots`")
                segs.append(p)
            card_png = end_card_png(ctx, W, H, tmp / f"endcard_{aspect}.png")
            card_mp4 = tmp / f"endcard_{aspect}.mp4"
            shots_stage.render_kenburns(card_png, card_mp4, W, H, ctx.sb["end_card"]["duration_s"], fps,
                                        {"zoom_from": 1.0, "zoom_to": 1.03, "pan": "none"}, "crop", 0.5, True, True)
            silent = concat(segs + [card_mp4], tmp / f"video_{aspect}.mp4")
            out = mux_with_subs(silent, mix, subs[aspect]["en"], aspect, final / f"film_{aspect}{suffix}.mp4")
            results[aspect] = out
            say(f"  ✓ {out.relative_to(ctx.out.parent) if ctx.out.parent in out.parents else out}")
        stats = {a: {"duration_s": round(probe_duration(p), 2), **measure_loudness(p)} for a, p in results.items()}
        rec.update(output={a: str(p) for a, p in results.items()}, extra=stats)
    (final / "export_report.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    for a, st in stats.items():
        say(f"    {a}: {st['duration_s']}s, {st.get('integrated_lufs')} LUFS, TP {st.get('true_peak_dbfs')} dBFS")
    return results


def run_radio(ctx: Ctx) -> Path:
    """Radio cut: narration + temp score on a black frame — the cheap prototype for user test #1."""
    say("▶ radio cut")
    total = film_duration(ctx.sb)
    out_dir = ctx.out / "radio"
    out_dir.mkdir(parents=True, exist_ok=True)
    music = StageCache(ctx.out, "music").current("score")
    if not music:
        raise RuntimeError("no score — run `python -m pipeline music` (placeholder is fine)")
    mix = build_mix(ctx, music, out_dir / "radio_cut.wav", total)
    subs = build_subtitles(ctx, out_dir)
    video = out_dir / "black.mp4"
    ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=24:d={total:.3f}", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-preset", "veryfast", video])
    out = out_dir / "radio_cut.mp4"
    with ctx.log.call(stage="radio", shot=None, provider="ffmpeg", model="radio-cut", params={"duration": total}) as rec:
        mux_with_subs(video, mix, subs["en"], "16x9", out)
        rec["output"] = str(out)
    video.unlink(missing_ok=True)
    say(f"  ✓ {out}  (also {mix.name} for WhatsApp/Telegram voice sharing)")
    return out
