"""Atlas normalization: identification only -- never value/status/scope."""
from serum2.reference.serum_atlas import (
    normalize_control, normalize_mod_source, EXACT, ALIAS, UNRESOLVED, AMBIGUOUS,
)
from serum2.source.visual_evidence import VisualEvidenceBundle, OBSERVED, OUT_OF_VIEW
from serum2.producer.visual_reasoner import ingest_stage_a_observation

PROV = {"observer": "claude_code", "observation_mode": "direct_visual_inspection", "model_api_used": False}


def _ingest(controls=(), routes=()):
    b = VisualEvidenceBundle(source_url="u", source_id="x", video_id="x")
    ingest_stage_a_observation(b, {"stage_a_provenance": PROV, "frames": [{
        "frame_id": "f1", "timestamp_sec": 1.0, "serum_visible": True,
        "controls": list(controls), "mod_routes": list(routes)}]})
    return b.ui_state_snapshots[0]


def _c(cid, **kw):
    return {"control_id": cid, "control_type": "knob", "status": "OBSERVED", **kw}


def test_exact_canonical_match():
    r = normalize_control("env1.release")
    assert (r.status, r.canonical_id) == (EXACT, "env1.release")
    assert normalize_control("OSC A Unison").canonical_id == "oscA.unison"


def test_unique_alias_match():
    r = normalize_control("oscA.wt_pos")
    assert (r.status, r.canonical_id) == (ALIAS, "oscA.wt_position")
    # the audit's FILTER1.TYPE_SPECIFIC.FREQ2 (label "FREQ") makes bare "Freq" genuinely ambiguous
    r = normalize_control("Filter 1 Freq")
    assert r.status == AMBIGUOUS and set(r.candidates) == {"filter1.cutoff", "filter1.type_specific.freq2"}


def test_ambiguous_alias():
    for t in ("cutoff", "release"):
        r = normalize_control(t)
        assert r.status == AMBIGUOUS and r.canonical_id is None and len(r.candidates) > 1
    assert normalize_control("cutoff").candidates == ("filter1.cutoff", "filter2.cutoff")
    # context can disambiguate; without it, nothing is guessed
    assert normalize_control("release", "ENV1 panel, REL knob").canonical_id == "env1.release"


def test_unknown_label():
    r = normalize_control("flux capacitor")
    assert r.status == UNRESOLVED and r.canonical_id is None


def test_explicit_filter1_and_filter2_cutoff():
    assert normalize_control("Filter 1 Cutoff") .canonical_id == "filter1.cutoff"
    assert normalize_control("Filter 2 Cutoff").canonical_id == "filter2.cutoff"
    assert normalize_control("Filter 1 Cutoff").status == EXACT


def test_raw_label_preserved_and_value_status_untouched():
    s = _ingest([_c("oscA.wt_pos", label="WT POS", value="12", screen_region="OSC A row")])
    c = s.controls[0]
    assert c.control_id == "oscA.wt_position"          # canonical
    assert c.label == "WT POS"                          # raw label kept
    assert c.resolution["raw_control_id"] == "oscA.wt_pos"
    assert c.resolution["status"] == ALIAS
    assert (c.value, c.status) == ("12", OBSERVED)      # untouched


def test_out_of_view_stays_out_of_view():
    s = _ingest([_c("filter1.cutoff", label="CUTOFF", value=None, status="OUT_OF_VIEW")])
    c = s.controls[0]
    assert c.status == OUT_OF_VIEW and c.value is None
    assert c.resolution["status"] == EXACT


def test_ambiguous_control_kept_not_dropped():
    s = _ingest([_c("cutoff", label="CUTOFF", value="500 Hz")])
    assert len(s.controls) == 1
    c = s.controls[0]
    assert c.control_id == "cutoff" and c.resolution["status"] == AMBIGUOUS
    assert c.value == "500 Hz"
    u = _ingest([_c("oscA.flux", label="FLUX")]).controls[0]
    assert u.control_id == "oscA.flux" and u.resolution["status"] == UNRESOLVED


def test_id_label_conflict_not_picked():
    c = _ingest([_c("filter1.cutoff", label="Filter 2 Cutoff")]).controls[0]
    assert c.resolution["status"] == AMBIGUOUS and c.control_id == "filter1.cutoff"


def test_modulation_source_and_destination():
    s = _ingest(routes=[{"source": "LFO 1", "destination": "Filter 1 Cutoff", "amount": None}])
    r = s.mod_routes[0]
    assert (r.source, r.destination) == ("lfo1", "filter1.cutoff")
    assert r.amount is None                              # nothing manufactured
    assert r.resolution["source"]["raw"] == "LFO 1"
    assert r.resolution["destination"]["raw"] == "Filter 1 Cutoff"
    f = _ingest(routes=[{"source": "LFO 1", "destination": "Filter 1 Freq"}]).mod_routes[0]
    assert f.destination == "Filter 1 Freq" and f.resolution["destination"]["status"] == AMBIGUOUS


def test_ambiguous_modulation_destination_stays_ambiguous():
    r = _ingest(routes=[{"source": "LFO 1", "destination": "Filter"}]).mod_routes[0]
    assert r.source == "lfo1"
    assert r.destination == "Filter"
    assert r.resolution["destination"]["status"] == AMBIGUOUS
    assert r.resolution["destination"]["canonical_id"] is None
    assert normalize_mod_source("LFO").status == AMBIGUOUS


def test_wavetable_identity_preserved():
    s = _ingest([
        _c("oscA.wavetable", control_type="dropdown", label="Wavetable", value="Analog_BD_Sin", screen_region="OSC A"),
        _c("oscA.wt_position", value="7", label="WT POS", screen_region="OSC A"),
    ])
    wt, pos = s.controls
    assert wt.control_id == "oscA.wavetable" and wt.value == "Analog_BD_Sin"   # raw name, no enum coercion
    assert pos.value == "7" and pos.frame_id == "f1" and wt.frame_id == "f1"
    assert wt.resolution["status"] == EXACT
    assert "wavetable" not in pos.resolution["canonical_id"].split(".")[1]      # index never becomes a name


def test_full_census_scope_unchanged():
    raw = [_c("oscA.unison", value="1"), _c("cutoff"), _c("mystery", value="3"),
           _c("matrix.routes", status="OUT_OF_VIEW"), _c("env1.release", value="15 ms")]
    s = _ingest(raw)
    assert len(s.controls) == len(raw)
    assert [c.value for c in s.controls] == ["1", None, "3", None, "15 ms"]
    assert [c.status for c in s.controls] == [r["status"] for r in raw]


def test_unknown_observer_id_not_rescued_by_label():
    c = _ingest([_c("lfo3.sync_division", label="RATE", value="1/4", screen_region="LFO3 panel")]).controls[0]
    assert c.control_id == "lfo3.sync_division" and c.resolution["status"] == UNRESOLVED
    assert c.resolution["label_hint"]["canonical_id"] == "lfo3.rate"   # hint only
