"""Fast, offline tests for the contract, caching and timing logic. Run: python -m pytest -q"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from pipeline.cache import StageCache, hash_inputs
from pipeline.context import Ctx
from pipeline.runlog import RunLog
from pipeline.stages import shots as shots_stage
from pipeline.storyboard import StoryboardError, _apply_defaults, film_duration, load, semantic_errors, shot_prompt, timeline
from pipeline.subtitles import chunk, cues_for_line, to_srt

FIX = Path(__file__).parent / "fixtures" / "demo_storyboard.json"


@pytest.fixture
def raw() -> dict:
    return json.loads(FIX.read_text(encoding="utf-8"))


def write(tmp_path: Path, sb: dict) -> Path:
    p = tmp_path / "sb.json"
    p.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    return p


# --- contract -----------------------------------------------------------------

def test_demo_storyboard_is_valid():
    sb = load(FIX)
    assert 60 <= film_duration(sb) <= 90
    assert [s.shot_id for s in timeline(sb)] == [s["id"] for s in sb["shots"]]


def test_schema_rejects_missing_reason(tmp_path, raw):
    del raw["shots"][0]["reason"]
    with pytest.raises(StoryboardError, match="reason"):
        load(write(tmp_path, raw))


def test_schema_requires_ai_disclosure_on_end_card(tmp_path, raw):
    raw["end_card"]["text"] = "Thanks for watching"
    with pytest.raises(StoryboardError):
        load(write(tmp_path, raw))


def test_duration_window_enforced(tmp_path, raw):
    for s in raw["shots"]:
        s["duration_s"] = 3
    with pytest.raises(StoryboardError, match="60–90"):
        load(write(tmp_path, raw))


def test_consent_gate_blocks_real_person_without_record(tmp_path, raw):
    raw["characters"][0]["real_person"] = True
    raw["characters"][0]["consent_ref"] = "C-99"
    ethics = tmp_path / "ETHICS.md"
    ethics.write_text("# Ethics\nno records yet\n", encoding="utf-8")
    errs = semantic_errors(_apply_defaults(raw), ethics)
    assert any("C-99" in e for e in errs)
    ethics.write_text("| C-99 | Etetu | video consent recorded |\n", encoding="utf-8")
    assert not any("C-99" in e for e in semantic_errors(_apply_defaults(raw), ethics))


def test_unknown_character_rejected(raw):
    raw["shots"][1]["characters"] = ["nobody"]
    assert any("unknown character" in e for e in semantic_errors(_apply_defaults(raw)))


def test_prompt_injects_character_and_style_verbatim():
    sb = load(FIX)
    s02 = sb["shots"][1]
    p = shot_prompt(sb, s02)
    assert sb["characters"][0]["description"] in p and sb["style"]["block"] in p


# --- caching ------------------------------------------------------------------

def test_hash_is_order_independent_and_sensitive():
    assert hash_inputs({"a": 1, "b": 2}) == hash_inputs({"b": 2, "a": 1})
    assert hash_inputs({"a": 1}) != hash_inputs({"a": 2})


def test_editing_one_shot_changes_only_that_shots_key():
    from pipeline.stages.keyframes import keyframe_inputs

    sb = load(FIX)
    ctx = Ctx(sb=sb, storyboard_path=FIX, out=Path("."), log=RunLog(Path(os.devnull)), mock=True)
    before = [hash_inputs(keyframe_inputs(ctx, s, s["keyframe"]["seed"], [])) for s in sb["shots"]]
    sb2 = copy.deepcopy(sb)
    sb2["shots"][2]["keyframe"]["prompt"] += " with a copper pan"
    ctx.sb = sb2
    after = [hash_inputs(keyframe_inputs(ctx, s, s["keyframe"]["seed"], [])) for s in sb2["shots"]]
    changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert changed == [2]


def test_stage_cache_roundtrip(tmp_path):
    c = StageCache(tmp_path, "x")
    key = hash_inputs({"k": 1})
    assert c.lookup("s01", key, ".txt") is None
    p = c.path_for("s01", key, ".txt")
    p.write_text("hi")
    c.record("s01", key, p)
    assert StageCache(tmp_path, "x").current("s01") == p


# --- timing -------------------------------------------------------------------

@pytest.mark.parametrize("dur", [2.0, 5.0, 8.0, 12.0])
def test_wan_frames_are_4k_plus_1(dur):
    n = shots_stage.wan_frames(dur)
    assert (n - 1) % 4 == 0 and n <= 121


def test_subtitle_chunks_respect_limits():
    text = "The third is bereka, the blessing. That day, for the first time in many years, I stayed until the very end."
    for block in chunk(text, 40, 2):
        lines = block.split("\n")
        assert len(lines) <= 2 and all(len(l) <= 40 for l in lines)


def test_cues_fill_voiced_window_and_srt_format():
    cues = cues_for_line("One two three four five six seven eight nine ten eleven twelve thirteen.", 10.0, 4.0)
    assert cues[0].start == 10.0 and cues[-1].end <= 14.0 + 1e-6
    srt = to_srt(cues)
    assert srt.startswith("1\n00:00:10,000 --> ")


def test_runlog_logs_failures(tmp_path):
    log = RunLog(tmp_path / "runs.jsonl")
    with pytest.raises(ValueError):
        with log.call(stage="t", shot="s01", provider="p", model="m"):
            raise ValueError("boom")
    rec = log.read()[-1]
    assert rec["status"] == "error" and "boom" in rec["error"] and rec["latency_s"] >= 0


# --- end to end (offline, ~1 min) ----------------------------------------------

@pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="set RUN_SLOW=1 to run the full mock film")
def test_mock_film_end_to_end(tmp_path):
    from pipeline.cli import main

    main(["--mock", "--draft", "--storyboard", str(FIX), "--out", str(tmp_path / "o"),
          "--runs", str(tmp_path / "runs.jsonl"), "film"])
    final = tmp_path / "o" / "final"
    assert (final / "film_16x9_draft.mp4").exists() and (final / "film_9x16_draft.mp4").exists()
    stats = json.loads((final / "export_report.json").read_text())
    assert abs(stats["16x9"]["duration_s"] - film_duration(load(FIX))) < 0.5
    assert abs(stats["16x9"]["integrated_lufs"] - (-14)) < 1.5


def test_pending_consent_detected(tmp_path, raw):
    from pipeline.storyboard import pending_consent

    raw["characters"][0].update(real_person=True, consent_ref="C-05")
    ethics = tmp_path / "ETHICS.md"
    ethics.write_text("| C-05 | Friend | PENDING: awaiting voice note |\n", encoding="utf-8")
    assert pending_consent(_apply_defaults(raw), ethics) == ["C-05"]
    ethics.write_text("| C-05 | Friend | voice note 2026-11-25 |\n", encoding="utf-8")
    assert pending_consent(_apply_defaults(raw), ethics) == []
