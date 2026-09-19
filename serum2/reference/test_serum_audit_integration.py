"""Frozen local UI audit (908 records) integrated into the ONE Atlas."""
import json
from pathlib import Path

import pytest

from serum2.reference import serum_audit as S
from serum2.reference import serum_ui_atlas as U
from serum2.reference.serum_atlas import (
    all_control_ids, get_control, normalize_control, atlas_provenance, AMBIGUOUS, EXACT, ALIAS,
)
from serum2.source.visual_evidence import VisualEvidenceBundle
from serum2.producer.visual_reasoner import ingest_stage_a_observation

PROV = {"observer": "claude_code", "observation_mode": "direct_visual_inspection", "model_api_used": False}
ARTIFACT = Path(__file__).parents[1] / "data/visual_frames/yt_89a28028e125/stage_a_observation_00018000.json"


def _by_sid():
    return {get_control(i).audit["semantic_id"]: i for i in all_control_ids() if get_control(i).audit}


def test_exact_audit_count_and_hash():
    a = S.load_audit()
    assert len(a["records"]) == 908 == a["manifest"]["semantic_count"]
    assert len({r["semantic_id"] for r in a["records"]}) == 908
    assert a["sha256"] == a["manifest"]["artifact_sha256"]


def test_tampered_audit_is_rejected(monkeypatch):
    monkeypatch.setattr(S, "_CACHE", None)
    monkeypatch.setattr(S.hashlib, "sha256", lambda b: type("H", (), {"hexdigest": lambda s: "0" * 64})())
    with pytest.raises(RuntimeError, match="hash"):
        S.load_audit()
    monkeypatch.undo()
    S._CACHE = None
    assert S.load_audit()["sha256"].startswith("fac5ced3")


def test_every_audit_record_is_in_the_single_registry_without_duplicates():
    ids = all_control_ids()
    assert len(ids) == len(set(ids))
    m = _by_sid()
    assert len(m) == 908 and len(set(m.values())) == 908     # 1 record -> 1 distinct canonical id


def test_provenance_preserved_verbatim():
    raw = {r["semantic_id"]: r for r in S.load_audit()["records"]}
    for sid, cid in _by_sid().items():
        rec = get_control(cid).audit
        assert rec == raw[sid] and rec["sources"] and rec["evidence_type"] and rec["status"]
        assert get_control(cid).audit_bridge in ("EXACT_NAME", "TABLE", "DERIVED_NEW")


def test_version_and_hash_provenance_exposed():
    p = atlas_provenance()
    assert p["serum_version"] == "2.0.21" and p["control_atlas_version"] == "serum-2.0.21-atlas-v1"
    assert p["ui_atlas_version"] == U.UI_ATLAS_VERSION
    assert p["source_audit_hash"] == S.load_audit()["manifest"]["artifact_sha256"]
    assert p["source_audit_version"].startswith("1.2.0") and p["source_audit_record_count"] == 908
    assert normalize_control("Filter 1 Cutoff").to_dict()["source_audit_hash"] == p["source_audit_hash"]


def test_wavetable_coverage_preserved_and_gaps_are_honest():
    m = _by_sid()
    for f in ("WT_POS", "UNI_WT_POS", "UNISON", "UNI_STACK", "UNI_DETUNE", "UNI_BLEND", "WARP", "WARP_MODE",
              "WARP_2", "WARP_2_MODE", "WARP_VAR", "PHASE", "RAND_PHASE", "OCTAVE", "SEMI", "FINE", "RATIO"):
        assert "OSC1.%s" % f in m, f
    assert m["OSC1.WT_POS"] == "oscA.wt_position" and m["OSC2.WARP_2_MODE"] == "oscB.warp_mode2"
    assert m["MIXER.OSC_A.ROUTING"]                         # oscillator routing is in the audit
    # NOT in the audit (so they come only from the PDF-derived supplement):
    assert not any("WAVETABLE" in s or s.endswith(".MODE") and s.startswith("OSC") for s in m)
    assert get_control("oscA.mode").source.startswith("ui-atlas-v2")
    assert get_control("oscA.wavetable").audit is None


def test_mode_dependence_kept_as_the_audit_states_it():
    d = U.describe("oscA.sample_loop_start")
    assert d["mode_dependent"] and d["audit_modes"] == ["WAVETABLE", "SAMPLE", "MULTISAMPLE", "GRANULAR", "SPECTRAL"]
    assert "Mode-dependent rendering" in d["conditional_visibility"]
    assert d["modes"] == ["SAMPLE", "GRANULAR", "SPECTRAL"]      # PDF placement, kept separate from the audit's
    w = U.describe("oscA.wt_position")
    assert w["mode_dependent"] and w["audit_modes"] and w["audit_id"] == "OSC1.WT_POS"
    # no per-mode split exists in the audit -> none is fabricated for audit-only fields
    assert U.describe("oscA.start")["modes"] == U.describe("oscA.start")["audit_modes"]


def test_graph_route_topology_information_preserved():
    m = _by_sid()
    assert get_control(m["MIXER.FILTER1.GRAPHIC_CUTOFF_RESONANCE"]).element_kind == "GRAPH"
    assert get_control(m["LFO1.WAVEFORM_GRAPH"]).control_id == "lfo1.curve_display"
    kinds = [get_control(i).element_kind for i in m.values()]
    assert kinds.count("GRAPH") >= 20 and kinds.count("ROUTE") >= 40 and kinds.count("TOPOLOGY") >= 5
    assert "REGION" not in kinds                            # the audit has no region model


def test_ambiguity_and_unknowns_survive_integration():
    assert normalize_control("cutoff").status == AMBIGUOUS
    assert normalize_control("Filter 1 Cutoff").canonical_id == "filter1.cutoff"
    assert normalize_control("Filter 1 Freq").status == AMBIGUOUS       # audit FREQ2 (13/107 filter types)
    assert normalize_control("release").status == AMBIGUOUS
    assert normalize_control("zzz nothing").status == "UNRESOLVED"


def test_reference_defaults_never_become_observed_values():
    d = get_control("macro1.value")
    assert d.default_value == 0.0
    b = VisualEvidenceBundle(source_url="u", source_id="x", video_id="x")
    ingest_stage_a_observation(b, {"stage_a_provenance": PROV, "frames": [{"frame_id": "f", "timestamp_sec": 0,
        "controls": [{"control_id": "macro1.value", "status": "OBSERVED", "value": None}]}]})
    assert b.ui_state_snapshots[0].controls[0].value is None


def test_census_scope_unchanged_by_audit():
    raw = [{"control_id": i, "status": "OBSERVED", "value": str(n)}
           for n, i in enumerate(["oscA.wt_position", "fx.sys.reorder", "totally.unknown", "cutoff"])]
    b = VisualEvidenceBundle(source_url="u", source_id="x", video_id="x")
    ingest_stage_a_observation(b, {"stage_a_provenance": PROV, "frames": [{"frame_id": "f", "timestamp_sec": 0, "controls": raw}]})
    c = b.ui_state_snapshots[0].controls
    assert [x.value for x in c] == ["0", "1", "2", "3"] and len(c) == 4


def test_schema_derived_273_ids_all_remain():
    v1 = [i for i in all_control_ids() if not (get_control(i).source.startswith(("ui-atlas", "audit:")))]
    assert len(v1) >= 273
    for must in ("env1.release", "oscA.unison", "oscA.wavetable", "filter1.cutoff", "lfo3.rate", "matrix.amount"):
        assert must in all_control_ids()


def test_lfo_7_to_10_are_sources_only():
    assert "lfo7.rate" not in all_control_ids() and "lfo6.rate" in all_control_ids()
    from serum2.reference.serum_atlas import normalize_mod_source
    assert normalize_mod_source("LFO 10").canonical_id == "lfo10"
    assert normalize_mod_source("LFO 11").status == "UNRESOLVED"


@pytest.mark.skipif(not ARTIFACT.exists(), reason="real mU6 Stage-A artifact lives in gitignored serum2/data")
def test_real_mu6_artifact_still_ingests():
    d = json.loads(ARTIFACT.read_text())
    raw = d["frames"][0]["controls"]
    b = VisualEvidenceBundle(source_url="u", source_id="x", video_id="x")
    ingest_stage_a_observation(b, d)
    cs = b.ui_state_snapshots[0].controls
    assert len(cs) == len(raw) == 24
    for r, c in zip(raw, cs):
        assert (c.value, c.status, c.label, c.unit) == (r["value"], r["status"], r["label"], r["unit"])
        assert c.resolution["raw_control_id"] == r["control_id"]
        assert c.resolution["source_audit_hash"] == S.load_audit()["sha256"]
    st = {c.control_id: c.status for c in cs}
    assert st["filter1.cutoff"] == "OUT_OF_VIEW" and st["matrix.routes"] == "OUT_OF_VIEW"
