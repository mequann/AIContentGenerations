"""Stages: references (character sheets) and keyframes (one still per shot).

Consistency strategy (see ARCHITECTURE.md):
  1. Generate a reference sheet per character first; a human picks the best candidate.
  2. Every keyframe prompt carries the character's fixed description + the style block verbatim.
  3. If the image model accepts reference images (FLUX.2), the chosen sheet is passed in.
  4. The keyframe cache key includes the reference file hash, so re-picking a reference
     regenerates exactly the shots that feature that character.
"""
from __future__ import annotations

from pathlib import Path

from ..cache import StageCache, file_hash, hash_inputs
from ..config import LIST_PRICE_USD, MODELS
from ..context import Ctx, say
from ..providers import mock
from ..retry import QuotaExhausted
from ..storyboard import shot_prompt


def _model(ctx: Ctx) -> str:
    return "mock" if ctx.mock else MODELS.cf_image


def _generate(ctx: Ctx, *, stage: str, item: str, prompt: str, seed: int, w: int, h: int,
              refs: list[Path], key: str, path: Path) -> None:
    with ctx.log.call(stage=stage, shot=item, provider="mock" if ctx.mock else "cloudflare", model=_model(ctx),
                      params={"width": w, "height": h, "steps": 4, "n_refs": len(refs), "prompt": prompt[:400]},
                      seed=seed, input_hash=key) as rec:
        if ctx.mock:
            data = mock.image(item, prompt, w, h, seed)
        else:
            from ..providers import cloudflare as cf

            use_refs = refs if cf.supports_references(MODELS.cf_image) else None
            res = cf.generate(prompt, model=MODELS.cf_image, seed=seed, width=w, height=h, references=use_refs)
            data = cf.fit_to(res.data, w, h)
            if res.note:
                rec["note"] = res.note
                ctx.warn(f"{item}: {res.note}")
            rec["cost_usd"] = LIST_PRICE_USD["cf_image_per_image"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        rec["output"] = str(path)


# ----------------------------------------------------------------------------- references

def reference_prompt(ctx: Ctx, char: dict) -> str:
    return (f"Character reference sheet of {char['name']}: full body front view and close-up portrait side by side, "
            f"neutral expression, even soft light, plain warm-grey background. {char['description'].strip()} "
            f"{ctx.sb['style']['block'].strip()}")


def run_references(ctx: Ctx) -> dict[str, Path]:
    cache = StageCache(ctx.out, "references")
    w, h = ctx.sb["style"]["image_width"], ctx.sb["style"]["image_height"]
    chosen: dict[str, Path] = {}
    say(f"▶ references ({_model(ctx)})")
    for char in ctx.sb["characters"]:
        prompt = reference_prompt(ctx, char)
        paths = []
        for i in range(char["candidates"]):
            seed = char["seed"] + i
            inputs = {"prompt": prompt, "seed": seed, "w": w, "h": h, "model": _model(ctx)}
            key = hash_inputs(inputs)
            item = f"{char['id']}_c{i}"
            hit = cache.lookup(item, key, ".png")
            if hit and not ctx.force:
                ctx.log.cache_hit("references", item, key, str(hit))
                paths.append(hit)
                continue
            path = cache.path_for(item, key, ".png")
            _generate(ctx, stage="references", item=item, prompt=prompt, seed=seed, w=w, h=h, refs=[], key=key, path=path)
            cache.record(item, key, path, inputs=inputs)
            paths.append(path)
            say(f"  + {item}")
        pick = paths[char["selected"]]
        cache.record(char["id"], file_hash(pick), pick, selected_candidate=char["selected"])
        chosen[char["id"]] = pick
        say(f"  ✓ {char['id']} → candidate {char['selected']} ({pick.name})")
    return chosen


# ----------------------------------------------------------------------------- keyframes

def keyframe_inputs(ctx: Ctx, shot: dict, seed: int, refs: list[Path]) -> dict:
    return {
        "prompt": shot_prompt(ctx.sb, shot),
        "negative": ctx.sb["style"].get("negative", ""),
        "seed": seed,
        "w": ctx.sb["style"]["image_width"],
        "h": ctx.sb["style"]["image_height"],
        "model": _model(ctx),
        "refs": [file_hash(r) for r in refs],
    }


def run_keyframes(ctx: Ctx) -> dict[str, Path]:
    refs_cache = StageCache(ctx.out, "references")
    cache = StageCache(ctx.out, "keyframes")
    out: dict[str, Path] = {}
    say(f"▶ keyframes ({_model(ctx)})")
    for shot in ctx.sb["shots"]:
        sid = shot["id"]
        refs = [p for c in shot["characters"] if (p := refs_cache.current(c))]
        if not ctx.selected(sid) and cache.current(sid):
            out[sid] = cache.current(sid)
            continue
        kf = shot["keyframe"]
        paths: list[Path] = []
        for i in range(kf["candidates"]):
            seed = kf["seed"] + i
            inputs = keyframe_inputs(ctx, shot, seed, refs)
            key = hash_inputs(inputs)
            item = f"{sid}_c{i}"
            hit = cache.lookup(item, key, ".png")
            if hit and not ctx.force:
                ctx.log.cache_hit("keyframes", item, key, str(hit))
                paths.append(hit)
                continue
            path = cache.path_for(item, key, ".png")
            try:
                _generate(ctx, stage="keyframes", item=item, prompt=inputs["prompt"], seed=seed,
                          w=inputs["w"], h=inputs["h"], refs=refs, key=key, path=path)
            except QuotaExhausted as e:
                ctx.warn(f"{item}: {e} — stopping keyframes; re-run tomorrow, cached shots are kept")
                return out
            cache.record(item, key, path, inputs={**inputs, "prompt": inputs["prompt"][:500]})
            paths.append(path)
            say(f"  + {item}")
        pick = paths[kf["selected"]]
        cache.record(sid, file_hash(pick), pick, selected_candidate=kf["selected"])
        out[sid] = pick
        say(f"  ✓ {sid} → candidate {kf['selected']} ({pick.name})")
    return out
