"""Architecture 29, 33.2, 33.3, 34: replay pins, readback route records, legacy episodes."""
import json
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from serum2.producer.contract_registry import ContractRegistry
from serum2.server.experience_record import (
    ProductionExperienceRecord, REPLAY_PIN_FIELDS, REPLAY_PROVENANCE_KEY, build_readback_record,
    is_canonical_serum_readback, replay_eligibility, stamp_replay_provenance, stamp_reference_provenance, save, load,
)

KEYS = ("envelope_field_decay", "envelope_field_sustain", "no_such_capability")
BACKENDS = {"serum_mcp": {"tool": "generate_preset", "version": "test"}, "serum": {"version": "2.0.21"}}
RB = [build_readback_record(domain="serum", route="DIRECT_UI", plugin="Serum", version="2.0.21",
                            delivery_route="ABLETON_UI_LOAD", watched=["a"], expected={"a": 1}, observed={"a": 1})]


def _rec():
    return ProductionExperienceRecord(experience_id="e", run_id="r")


def test_replay_pins_cover_every_field_the_architecture_names():
    rec = _rec()
    stamp_reference_provenance(rec)
    stamp_replay_provenance(rec, ContractRegistry(), KEYS, BACKENDS, RB)
    pins = rec.provenance[REPLAY_PROVENANCE_KEY]
    assert all(pins[f] for f in REPLAY_PIN_FIELDS)
    assert pins["capability_contract_versions"]["envelope_field_decay"]["status"] == "CAUSAL_VERIFIED"
    assert pins["capability_binding_versions"]["envelope_field_decay"]["host_parameter_name"] == "Env 1 Decay"
    assert pins["capability_contract_versions"]["no_such_capability"] is None          # recorded as absent, not invented
    assert all(len(v) == 64 for v in pins["brain_logic_version"].values())            # code hashes, not labels
    assert replay_eligibility(rec) == {"status": "REPLAYABLE", "replay_execute": True, "replay_simulate": True, "missing": []}


def test_pins_survive_a_round_trip_exactly(tmp_path):
    rec = _rec()
    stamp_reference_provenance(rec)
    stamp_replay_provenance(rec, ContractRegistry(), KEYS, BACKENDS, RB)
    save(rec, tmp_path)
    back = load("e", tmp_path)
    assert back.provenance[REPLAY_PROVENANCE_KEY] == rec.provenance[REPLAY_PROVENANCE_KEY]


def test_existing_pins_are_never_overwritten():
    rec = _rec()
    rec.provenance[REPLAY_PROVENANCE_KEY] = {"marker": 1}
    stamp_replay_provenance(rec, ContractRegistry(), KEYS, BACKENDS, RB)
    assert rec.provenance[REPLAY_PROVENANCE_KEY] == {"marker": 1}


def test_legacy_episode_is_marked_not_reinterpreted():
    e = replay_eligibility(_rec())
    assert e["status"] == "LEGACY_NO_PROVENANCE" and not e["replay_execute"] and not e["replay_simulate"]


def test_reference_only_episode_can_simulate_but_not_execute():
    rec = _rec()
    stamp_reference_provenance(rec)
    e = replay_eligibility(rec)
    assert e["status"] == "REFERENCE_ONLY" and e["replay_simulate"] and not e["replay_execute"]
    assert set(e["missing"]) == set(REPLAY_PIN_FIELDS)


def test_missing_backend_or_readback_pin_blocks_execute():
    rec = _rec()
    stamp_reference_provenance(rec)
    stamp_replay_provenance(rec, ContractRegistry(), KEYS, {}, [])                      # nothing actually recorded
    e = replay_eligibility(rec)
    assert not e["replay_execute"] and {"execution_backend_versions", "readback_route_versions"} <= set(e["missing"])


def test_only_direct_ui_readback_is_canonical_for_serum():
    def rb(route):
        return build_readback_record(domain="serum", route=route, plugin="Serum", version="2.0.21", delivery_route=None,
                                     watched=["a"], expected={"a": 1}, observed={"a": 1})
    assert is_canonical_serum_readback(rb("DIRECT_UI"))
    for other in ("PLUGIN_HOST_READBACK", "STANDALONE_PLUGIN_INSPECTION", "SCREEN_INSPECTION"):
        assert not is_canonical_serum_readback(rb(other))                                # a match on another route is not verification


def test_readback_comparison_is_computed_not_asserted():
    r = build_readback_record(domain="serum", route="DIRECT_UI", plugin="Serum", version="2.0.21", delivery_route="ABLETON_UI_LOAD",
                              watched=["a", "b"], expected={"a": 1, "b": 2}, observed={"a": 1, "b": 3})
    assert r["comparison"] == {"a": True, "b": False} and r["all_match"] is False and not is_canonical_serum_readback(r)
    assert build_readback_record(domain="serum", route="DIRECT_UI", plugin="Serum", version="2.0.21", delivery_route=None,
                                 watched=[], expected={}, observed={})["all_match"] is False    # nothing watched -> no claim


def test_unknown_readback_route_is_rejected():
    with pytest.raises(ValueError):
        build_readback_record(domain="serum", route="ABLETON_HOST", plugin="Serum", version="2.0.21", delivery_route=None,
                              watched=[], expected={}, observed={})
