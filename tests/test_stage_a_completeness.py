"""A6 Completeness: stage_a_is_filled uses all() over serum_visible frames.

Proves that:
  - 1 analysed frame out of 300 total is NOT sufficient (all() change)
  - All frames with serum_visible=True must have controls/mod_routes
  - An all-not-serum-visible file returns False
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from youtube_to_serum.reference_engine import stage_a_is_filled


def _make_skeleton(frames):
    return {"frames": [{"controls": [], "mod_routes": [], "observations": [], "unknown": [], **f}
                       for f in frames]}


def _write_skeleton(tmp_path, frames):
    p = tmp_path / "skeleton.json"
    p.write_text(json.dumps(_make_skeleton(frames)))
    return str(p)


def test_all_not_serum_visible_returns_false(tmp_path):
    frames = [{"serum_visible": False} for _ in range(10)]
    assert stage_a_is_filled(_write_skeleton(tmp_path, frames)) is False


def test_one_serum_visible_with_no_controls_returns_false(tmp_path):
    frames = [{"serum_visible": True, "controls": [], "mod_routes": []}]
    frames += [{"serum_visible": False} for _ in range(9)]
    assert stage_a_is_filled(_write_skeleton(tmp_path, frames)) is False


def test_one_of_300_analysed_not_sufficient(tmp_path):
    """The original any()-based check accepted this; all() must reject it."""
    frames = [{"serum_visible": True, "controls": [{"control_id": "env2.decay", "value": "300"}]}]
    frames += [{"serum_visible": True, "controls": []} for _ in range(299)]
    assert stage_a_is_filled(_write_skeleton(tmp_path, frames)) is False


def test_all_serum_visible_all_analysed(tmp_path):
    frames = [{"serum_visible": True, "controls": [{"control_id": "env2.decay", "value": "300"}]} for _ in range(5)]
    assert stage_a_is_filled(_write_skeleton(tmp_path, frames)) is True


def test_mixed_serum_visible_all_analysed(tmp_path):
    """serum_visible=False frames are ignored; all True frames must be analysed."""
    frames = [{"serum_visible": True, "controls": [{"control_id": "env2.decay", "value": "300"}]},
              {"serum_visible": False},
              {"serum_visible": True, "controls": [{"control_id": "env2.attack", "value": "5"}]},
              {"serum_visible": None}]
    assert stage_a_is_filled(_write_skeleton(tmp_path, frames)) is True


def test_one_unanalysed_serum_frame_fails(tmp_path):
    frames = [{"serum_visible": True, "controls": [{"control_id": "env2.decay", "value": "300"}]},
              {"serum_visible": True, "controls": []}]
    assert stage_a_is_filled(_write_skeleton(tmp_path, frames)) is False


def test_mod_routes_count_as_analysed(tmp_path):
    frames = [{"serum_visible": True, "controls": [], "mod_routes": [{"source": "lfo1", "destination": "env1.attack"}]}]
    assert stage_a_is_filled(_write_skeleton(tmp_path, frames)) is True
