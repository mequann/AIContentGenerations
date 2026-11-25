"""Stage: moving shots.

Two sources per shot:
  * engine="wan"      → a Wan 2.2 TI2V-5B clip generated on Kaggle (export → run notebook → import).
                        If the clip for the current inputs is missing, we fall back to Ken Burns and
                        log a `fallback` event, so the film always renders.
  * engine="kenburns" → slow pan/zoom over the keyframe, rendered locally with FFmpeg.
  * engine="still"    → hold the keyframe.

Each source is then conformed to both delivery formats (16:9 and 9:16) as a
fixed-length, silent H.264 segment. Segments are cached on a hash of their
inputs, so changing one shot re-renders only that shot.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageFilter

from ..cache import StageCache, file_hash, hash_inputs
from ..config import LIST_PRICE_USD, MODELS, RENDER, ROOT
from ..context import Ctx, say
from ..media import probe_duration, run as ffmpeg

STAGE = "shots"
FADE_S = 0.5
WAN_FPS = 24
WAN_PRESETS = {"480p": (832, 480), "720p": (1280, 704)}


def sizes(ctx: Ctx) -> dict[str, tuple[int, int]]:
    s = RENDER.draft_scale if ctx.draft else 1.0
    ev = lambda v: int(v * s) // 2 * 2  # noqa: E731  even dimensions for yuv420p
    return {"16x9": (ev(RENDER.landscape[0]), ev(RENDER.landscape[1])),
            "9x16": (ev(RENDER.portrait[0]), ev(RENDER.portrait[1]))}


# ----------------------------------------------------------------------------- Wan 2.2 (Kaggle)

def wan_frames(duration_s: float) -> int:
    """Wan wants 4k+1 frames; cap at 121 (≈5 s @ 24 fps) where quality is most stable."""
    n = min(121, max(33, int(round(duration_s * WAN_FPS))))
    return (n - 1) // 4 * 4 + 1


def wan_inputs(ctx: Ctx, shot: dict, keyframe: Path, resolution: str = "480p") -> dict:
    m = shot["motion"]
    return {
        "keyframe": file_hash(keyframe),
        "prompt": (m.get("prompt") or "").strip(),
        "negative": ctx.sb["style"].get("negative", ""),
        "seed": m["seed"],
        "frames": wan_frames(shot["duration_s"]),
        "resolution": resolution,
        "model": MODELS.wan,
    }


def wan_dir(ctx: Ctx) -> Path:
    d = ctx.out / STAGE / "wan"
    d.mkdir(parents=True, exist_ok=True)
    return d


def wan_clip(ctx: Ctx, shot: dict, keyframe: Path) -> Path | None:
    key = hash_inputs(wan_inputs(ctx, shot, keyframe))
    p = wan_dir(ctx) / f"{shot['id']}__{key[:12]}.mp4"
    return p if p.exists() and p.stat().st_size > 0 else None


def export_jobs(ctx: Ctx, dest: Path | None = None, resolution: str = "480p") -> Path:
    """Write a Kaggle job bundle: jobs.json + keyframes. Upload the folder as a Kaggle Dataset."""
    kf = StageCache(ctx.out, "keyframes")
    dest = Path(dest or ROOT / "kaggle" / "jobs")
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "keyframes").mkdir(parents=True)
    w, h = WAN_PRESETS[resolution]
    jobs = []
    for shot in ctx.sb["shots"]:
        if shot["motion"]["engine"] != "wan" or not ctx.selected(shot["id"]):
            continue
        img = kf.current(shot["id"])
        if not img:
            ctx.warn(f"{shot['id']}: no keyframe yet — run keyframes first")
            continue
        inputs = wan_inputs(ctx, shot, img, resolution)
        key = hash_inputs(inputs)
        if (wan_dir(ctx) / f"{shot['id']}__{key[:12]}.mp4").exists() and not ctx.force:
            say(f"  ✓ {shot['id']} already has a clip for these inputs — skipped")
            continue
        shutil.copy2(img, dest / "keyframes" / f"{shot['id']}.png")
        jobs.append({
            "shot": shot["id"], "image": f"keyframes/{shot['id']}.png",
            "prompt": inputs["prompt"] or "subtle natural motion, gentle camera push-in",
            "negative": inputs["negative"], "seed": inputs["seed"], "num_frames": inputs["frames"],
            "width": w, "height": h, "fps": WAN_FPS, "model": MODELS.wan,
            "output_name": f"{shot['id']}__{key[:12]}.mp4", "input_hash": key,
        })
    (dest / "jobs.json").write_text(json.dumps({"jobs": jobs}, indent=2, ensure_ascii=False), encoding="utf-8")
    say(f"  ⇢ {len(jobs)} Wan job(s) written to {dest} — upload as a Kaggle Dataset, run kaggle/wan22_i2v.py")
    return dest


def import_clips(ctx: Ctx, src: Path) -> int:
    """Copy Kaggle outputs in and merge their per-job logs into runs.jsonl."""
    src = Path(src)
    n = 0
    for mp4 in sorted(src.rglob("s[0-9][0-9]__*.mp4")):
        if re.fullmatch(r"s\d\d__[0-9a-f]{12}\.mp4", mp4.name):
            shutil.copy2(mp4, wan_dir(ctx) / mp4.name)
            n += 1
    for logf in src.rglob("results.jsonl"):
        for line in logf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            gpu_s = float(r.get("gpu_s", r.get("latency_s", 0)))
            ctx.log.write(stage=STAGE, shot=r.get("shot"), event="model_call", provider="kaggle",
                          model=r.get("model", MODELS.wan), params=r.get("params", {}), seed=r.get("seed"),
                          latency_s=r.get("latency_s"), gpu_s=gpu_s, status=r.get("status", "ok"),
                          error=r.get("error"), input_hash=r.get("input_hash"), output=r.get("output"),
                          cost_usd=round(gpu_s / 3600 * LIST_PRICE_USD["gpu_t4_per_hour"] * r.get("n_gpus", 1), 4),
                          imported_from=str(logf))
    say(f"  ⇠ imported {n} clip(s) from {src}")
    return n


# ----------------------------------------------------------------------------- rendering

def _prepare_still(img: Path, out: Path, W: int, H: int, mode: str, focus_x: float, scale: float = 2.0) -> Path:
    """Compose the keyframe onto the target frame at `scale`× size (oversampling removes zoompan jitter)."""
    im = Image.open(img).convert("RGB")
    TW, TH = int(W * scale), int(H * scale)
    target = TW / TH
    w, h = im.size
    if mode == "blurpad" and w / h > target + 0.01:
        bg = im.copy()
        bw = int(h * target)
        x0 = int((w - bw) * focus_x)
        bg = bg.crop((x0, 0, x0 + bw, h)).resize((TW, TH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(TW // 25))
        fg = im.resize((TW, int(h * TW / w)), Image.LANCZOS)
        bg.paste(fg, (0, (TH - fg.height) // 2))
        im = bg
    else:  # cover-crop around focus_x
        if w / h > target:
            nw = int(h * target)
            x0 = int(round((w - nw) * focus_x))
            im = im.crop((x0, 0, x0 + nw, h))
        else:
            nh = int(w / target)
            im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        im = im.resize((TW, TH), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG")
    return out


def _fades(dur: float, fade_in: bool, fade_out: bool) -> str:
    f = []
    if fade_in:
        f.append(f"fade=t=in:st=0:d={FADE_S}")
    if fade_out:
        f.append(f"fade=t=out:st={max(0, dur - FADE_S):.3f}:d={FADE_S}")
    return ("," + ",".join(f)) if f else ""


def _enc(fps: int) -> list[str]:
    return ["-r", str(fps), "-c:v", "libx264", "-preset", RENDER.preset, "-crf", str(RENDER.crf),
            "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart"]


def render_kenburns(img: Path, out: Path, W: int, H: int, dur: float, fps: int, kb: dict,
                    mode: str, focus_x: float, fade_in: bool, fade_out: bool) -> None:
    tmp = out.with_suffix(".prep.png")
    _prepare_still(img, tmp, W, H, mode, focus_x)
    N = max(2, int(round(dur * fps)))
    zf, zt, pan = kb["zoom_from"], kb["zoom_to"], kb["pan"]
    if pan != "none":  # panning needs headroom beyond the frame
        zf, zt = max(zf, 1.08), max(zt, 1.08)
    prog = f"on/{N - 1}"
    px = {"left": f"(1-{prog})", "right": prog}.get(pan, "0.5")
    py = {"up": f"(1-{prog})", "down": prog}.get(pan, "0.5")
    z = f"{zf}+({zt}-{zf})*{prog}"
    vf = (f"zoompan=z='{z}':x='(iw-iw/zoom)*{px}':y='(ih-ih/zoom)*{py}':d={N}:s={W}x{H}:fps={fps},"
          f"format=yuv420p{_fades(dur, fade_in, fade_out)}")
    ffmpeg(["-i", tmp, "-vf", vf, "-frames:v", N, *_enc(fps), out])
    tmp.unlink(missing_ok=True)


def render_clip(clip: Path, out: Path, W: int, H: int, dur: float, fps: int, trim: float,
                mode: str, focus_x: float, fade_in: bool, fade_out: bool) -> None:
    portrait = H > W
    if portrait and mode == "blurpad":
        fc = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3[bg];"
              f"[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2,")
    elif portrait:
        fc = (f"[0:v]crop='min(iw,ih*{W}/{H})':ih:'(iw-min(iw,ih*{W}/{H}))*{focus_x}':0,"
              f"scale={W}:{H}:flags=lanczos,")
    else:
        fc = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
    fc += (f"fps={fps},tpad=stop_mode=clone:stop_duration={dur:.3f},trim=duration={dur:.3f},setpts=PTS-STARTPTS,"
           f"format=yuv420p{_fades(dur, fade_in, fade_out)}[v]")
    ffmpeg(["-ss", f"{trim:.3f}", "-i", clip, "-filter_complex", fc, "-map", "[v]", *_enc(fps), out])


def run(ctx: Ctx) -> dict[str, dict[str, Path]]:
    kf_cache = StageCache(ctx.out, "keyframes")
    cache = StageCache(ctx.out, STAGE)
    fps = ctx.sb["meta"]["fps"]
    shots = ctx.sb["shots"]
    out: dict[str, dict[str, Path]] = {"16x9": {}, "9x16": {}}
    say(f"▶ shots ({'draft' if ctx.draft else 'final'} size)")
    for i, shot in enumerate(shots):
        sid = shot["id"]
        img = kf_cache.current(sid)
        if not img:
            raise RuntimeError(f"{sid}: no keyframe — run `python -m pipeline keyframes` first")
        m = shot["motion"]
        clip = wan_clip(ctx, shot, img) if m["engine"] == "wan" else None
        if m["engine"] == "wan" and not clip:
            ctx.log.write(stage=STAGE, shot=sid, event="fallback", detail="wan clip missing → kenburns")
            say(f"  · {sid}: no Wan clip for current inputs → Ken Burns fallback")
        source_kind = "wan" if clip else ("still" if m["engine"] == "still" else "kenburns")
        source = clip or img
        fade_in = i == 0 or shot["transition"] == "fade"
        fade_out = i == len(shots) - 1 or shots[i + 1]["transition"] == "fade"
        kb = {"zoom_from": 1.0, "zoom_to": 1.0, "pan": "none"} if source_kind == "still" else m["kenburns"]
        for aspect, (W, H) in sizes(ctx).items():
            inputs = {"source": file_hash(source), "kind": source_kind, "dur": shot["duration_s"], "fps": fps,
                      "size": [W, H], "kb": kb if source_kind != "wan" else None, "trim": m["trim_start_s"],
                      "vertical": shot["vertical"] if aspect == "9x16" else None,
                      "fade": [fade_in, fade_out], "v": 2}
            key = hash_inputs(inputs)
            item = f"{sid}_{aspect}"
            hit = cache.lookup(item, key, ".mp4")
            if hit and not (ctx.force and ctx.selected(sid)):
                ctx.log.cache_hit(STAGE, item, key, str(hit))
                cache.record(item, key, hit, kind=source_kind)
                out[aspect][sid] = hit
                continue
            path = cache.path_for(item, key, ".mp4")
            mode, fx = shot["vertical"]["mode"], shot["vertical"]["focus_x"]
            with ctx.log.call(stage=STAGE, shot=item, provider="ffmpeg", model=f"render:{source_kind}",
                              params={"size": [W, H], "dur": shot["duration_s"]}, input_hash=key) as rec:
                if source_kind == "wan":
                    render_clip(source, path, W, H, shot["duration_s"], fps, m["trim_start_s"], mode, fx, fade_in, fade_out)
                else:
                    render_kenburns(source, path, W, H, shot["duration_s"], fps, kb, mode, fx, fade_in, fade_out)
                rec["output"] = str(path)
            got = probe_duration(path)
            if abs(got - shot["duration_s"]) > 1.5 / fps:
                ctx.warn(f"{item}: rendered {got:.3f}s, expected {shot['duration_s']}s")
            cache.record(item, key, path, kind=source_kind)
            out[aspect][sid] = path
            say(f"  + {item} ({source_kind})")
    return out
