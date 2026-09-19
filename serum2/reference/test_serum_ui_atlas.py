"""UI State Atlas v2: structure over the one registry; identification only."""
from serum2.reference import serum_ui_atlas as U
from serum2.reference.serum_atlas import (
    all_control_ids, get_control, normalize_control, EXACT, ALIAS, AMBIGUOUS, UNRESOLVED,
)
from serum2.source.visual_evidence import VisualEvidenceBundle, OBSERVED, OUT_OF_VIEW
from serum2.producer.visual_reasoner import ingest_stage_a_observation

PROV = {"observer": "claude_code", "observation_mode": "direct_visual_inspection", "model_api_used": False}


def _snap(controls):
    b = VisualEvidenceBundle(source_url="u", source_id="x", video_id="x")
    ingest_stage_a_observation(b, {"stage_a_provenance": PROV, "frames": [{
        "frame_id": "f1", "timestamp_sec": 1.0, "serum_visible": True, "controls": controls}]})
    return b.ui_state_snapshots[0]


def _c(cid, **kw):
    return {"control_id": cid, "control_type": "other", "status": "OBSERVED", **kw}


def test_oscillator_mode_is_first_class():
    osc = U.SURFACES["oscillator"]
    assert [m.mode_id for m in osc.modes] == ["WAVETABLE", "MULTISAMPLE", "SAMPLE", "GRANULAR", "SPECTRAL"]
    mode = next(e for e in osc.common if e.element_id == "mode")
    assert mode.kind == U.SELECTOR and set(mode.values) == {"WAVETABLE", "MULTISAMPLE", "SAMPLE", "GRANULAR", "SPECTRAL"}
    assert normalize_control("oscA.mode").status == EXACT
    s = _snap([_c("oscA.mode", control_type="dropdown", value="WAVETABLE")])
    assert s.controls[0].value == "WAVETABLE" and s.controls[0].resolution["placement"]["surface"] == "oscillator"


def test_mode_specific_state_is_mode_scoped():
    wt = {e.element_id for e in U.elements_for("oscillator", "WAVETABLE")}
    sm = {e.element_id for e in U.elements_for("oscillator", "SAMPLE")}
    assert {"wt_position", "wt_interpolation_mode", "tuning_mode", "warp_mode2", "phase", "random_phase"} <= wt
    assert "loop_region" not in wt and "wt_position" not in sm
    assert {"loop_region", "sample_region", "slicing_mode", "sample_loop_crossfade"} <= sm
    assert "grain_count" in {e.element_id for e in U.elements_for("oscillator", "GRANULAR")}
    assert "spectral_freq_range" in {e.element_id for e in U.elements_for("oscillator", "SPECTRAL")}
    assert U.describe("oscA.loop_region")["modes"] == ["SAMPLE", "GRANULAR", "SPECTRAL"]
    assert U.describe("oscA.mode")["modes"] == []          # common to every mode


def test_graph_state_representable_with_detail():
    assert U.describe("oscA.sample_display")["kind"] == U.GRAPH
    assert U.describe("lfo1.curve_display")["kind"] == U.GRAPH
    assert U.describe("oscA.loop_region")["kind"] == U.REGION
    d = {"loop_start": "6", "loop_end": "45", "loop_mode": "FWD LOOP"}
    c = _snap([_c("oscA.loop_region", control_type="region", value="LS 6 / LE 45", detail=d)]).controls[0]
    assert c.detail == d and c.value == "LS 6 / LE 45" and c.resolution["status"] == EXACT


def test_selectors_and_text_identities():
    assert U.describe("oscA.warp_mode")["kind"] == U.SELECTOR
    assert U.describe("oscA.wavetable")["kind"] == U.TEXT_IDENTITY
    assert U.describe("oscA.sample_identity")["kind"] == U.TEXT_IDENTITY
    c = _snap([_c("oscA.sample_identity", control_type="text", value="Ocho Cero Ocho")]).controls[0]
    assert c.value == "Ocho Cero Ocho" and c.resolution["status"] == EXACT   # raw name untouched
    assert get_control("oscA.tuning_mode").enum_values == ("semitone", "harmonics", "ratio", "step")


def test_topology_and_routing_representable():
    for cid, kind in (("oscA.routing", U.ROUTE), ("matrix.routes", U.ROUTE), ("matrix.order", U.TOPOLOGY),
                      ("topology.filter_output_routing", U.TOPOLOGY)):
        assert U.describe(cid)["kind"] == kind, cid
    d = {"order": ["FXDistortion", "FXPhaser"], "bypassed": []}
    c = _snap([_c("fx.sys.reorder", control_type="topology", detail=d)]).controls[0]  # audit FX.SYS.REORDER
    assert c.detail == d and c.resolution["status"] == EXACT
    assert set(get_control("oscA.routing").enum_values) == {"Filter", "Main", "Direct", "None"}


def test_unknown_state_stays_unknown():
    c = _snap([_c("oscA.wt_position", value=None, status="AMBIGUOUS"),
               _c("oscA.loop_region", status="OUT_OF_VIEW")]).controls
    assert c[0].value is None and c[0].status == "AMBIGUOUS"
    assert c[1].status == OUT_OF_VIEW and c[1].value is None and c[1].detail is None


def test_normalization_does_not_manufacture_observations():
    # reference default / enum vocabulary never becomes an observed value
    c = _snap([_c("oscA.mode", value=None), _c("oscA.tuning_mode")]).controls
    assert all(x.value is None and x.detail is None for x in c)
    # a wt_position never yields a wavetable identity
    p = _snap([_c("oscA.wt_position", value="12")]).controls[0]
    assert p.resolution["canonical_id"] == "oscA.wt_position" and p.value == "12"


def test_full_census_scope_unchanged_by_atlas():
    raw = [_c("oscA.mode", value="SAMPLE"), _c("oscA.some_unlisted_thing", value="3"),
           _c("cutoff", value="500 Hz"), _c("oscA.wt_position", value="1")]  # mode/element mismatch kept
    s = _snap(raw)
    assert [c.value for c in s.controls] == ["SAMPLE", "3", "500 Hz", "1"]
    assert s.controls[1].resolution["status"] == UNRESOLVED and s.controls[2].resolution["status"] == AMBIGUOUS


def test_existing_273_controls_remain_compatible():
    ids = set(all_control_ids())
    for must in ("env1.release", "oscA.unison", "oscA.wavetable", "filter1.cutoff", "lfo3.rate",
                 "matrix.amount", "global.master_volume", "oscA.wt_position", "oscC.random_phase"):
        assert must in ids
    v1 = [i for i in ids if (get_control(i).source or "") and not get_control(i).source.startswith("ui-atlas")]
    assert len(v1) >= 273 and len(ids) > 273 and len(ids) == len(set(ids))
    # every element claiming source "schema" is a real schema entry, not a v2 invention
    for cid, e, _, _ in U._all_entries():
        if e.source == "schema":
            assert not get_control(cid).source.startswith("ui-atlas"), cid


def test_ambiguity_semantics_preserved_with_v2():
    assert normalize_control("cutoff").status == AMBIGUOUS
    assert normalize_control("Filter 1 Cutoff").canonical_id == "filter1.cutoff"
    assert normalize_control("OSC A Unison").canonical_id == "oscA.unison"
    assert normalize_control("Filter").canonical_id is None


def test_unestablished_things_are_not_invented():
    # p9 places timbre shifting on the MULTISAMPLE panel, not SPECTRAL
    assert U.describe("oscA.timbre")["modes"] == ["MULTISAMPLE"]
    assert "spectral_freq_range" in get_control("oscA.spectral_freq_range").control_id
    assert get_control("oscA.spectral_freq_range").unit is None and get_control("oscA.spectral_freq_range").min_value is None
    assert get_control("oscA.crs").notes and "not established" in get_control("oscA.crs").notes
