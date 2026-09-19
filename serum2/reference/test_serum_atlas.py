"""Deterministic tests for the Serum 2.0.21 Reference Atlas.

Covers exactly the required-validation list: version identity, stable
canonical IDs, no duplicates, alias resolution, reference-vs-episode
separation, no execution authority, and that ingest_stage_a_observation()
(the Stage-A boundary) still works unaffected by this addition.
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_atlas_version_identity():
    from serum2.reference.serum_atlas import ATLAS_VERSION, SERUM_VERSION
    assert ATLAS_VERSION == "serum-2.0.21-atlas-v1"
    assert SERUM_VERSION == "2.0.21"
    print("[PASS] test_atlas_version_identity")


def test_canonical_ids_are_stable_across_calls():
    from serum2.reference.serum_atlas import all_control_ids
    ids1 = all_control_ids()
    ids2 = all_control_ids()
    assert ids1 == ids2
    assert len(ids1) > 100  # real schema-derived breadth, not a stub
    for expected in ("env1.release", "env1.attack", "oscA.unison", "oscA.wavetable",
                      "filter1.cutoff", "lfo3.rate", "matrix.amount", "global.master_volume"):
        assert expected in ids1, "%s missing from the atlas" % expected
    print("[PASS] test_canonical_ids_are_stable_across_calls")


def test_no_duplicate_canonical_ids():
    from serum2.reference.serum_atlas import all_control_ids
    ids = all_control_ids()
    assert len(ids) == len(set(ids))
    print("[PASS] test_no_duplicate_canonical_ids")


def test_aliases_resolve_to_one_canonical_control():
    """Only an UNAMBIGUOUS alias yields a canonical id; shared aliases stay AMBIGUOUS
    (the old resolve_alias masked 'cut off' as filter1.cutoff)."""
    from serum2.reference.serum_atlas import normalize_control, ALIAS, AMBIGUOUS, UNRESOLVED
    r = normalize_control("smooth interpolation", "OSC A row")
    assert (r.status, r.canonical_id) == (ALIAS, "oscA.wt_interpolation_mode")
    r = normalize_control("cut off")
    assert r.status == AMBIGUOUS and r.canonical_id is None
    assert normalize_control("something that matches nothing at all xyz123").status == UNRESOLVED
    print("[PASS] test_aliases_resolve_to_one_canonical_control")


def test_reference_default_state_is_not_episode_evidence():
    """The Atlas's default_value is Serum's own shipped default -- it must
    never be confused with, or override, a real observed episode value.
    This test locks the DISTINCTION, not a specific number: get_control()
    returns a value under the explicit name `default_value` (reference
    knowledge only), and nothing in this module accepts or stores an
    'observed' value at all -- that vocabulary belongs solely to
    visual_evidence.ControlState."""
    from serum2.reference.serum_atlas import get_control
    from serum2.source.visual_evidence import ControlState, OBSERVED
    import dataclasses

    ref = get_control("env1.release")
    assert ref.default_value == 0.015  # Serum's shipped default, 15ms in seconds

    ref_fields = {f.name for f in dataclasses.fields(ref)}
    observed_only_fields = {"status", "frame_id", "frame_hash", "timestamp_sec", "confidence"}
    assert not (ref_fields & observed_only_fields), (
        "ReferenceControl must never grow observation-only fields -- that "
        "would blur reference knowledge with episode evidence"
    )

    # A real episode observation of the SAME control can legitimately
    # disagree with the reference default -- and must win as episode truth.
    observed = ControlState(control_id="env1.release", control_type="knob",
                             value="36 ms", status=OBSERVED)
    assert observed.value == "36 ms" != ref.default_value
    print("[PASS] test_reference_default_state_is_not_episode_evidence")


def test_atlas_has_no_execution_authority_surface():
    """The module must expose only lookup functions -- no admit/execute/
    resolve verbs, and ReferenceControl carries no execution_binding-shaped
    field. Guards against the Atlas quietly growing into a second authority
    layer."""
    from serum2.reference import serum_atlas
    forbidden_verbs = ("admit", "execute", "resolve_capability", "bind")
    public_names = [n for n in dir(serum_atlas) if not n.startswith("_")]
    for name in public_names:
        for verb in forbidden_verbs:
            assert verb not in name.lower(), (
                "serum_atlas.%s looks like an execution-authority surface -- "
                "the Atlas must stay read-only reference knowledge" % name
            )
    import dataclasses
    from serum2.reference.serum_atlas import ReferenceControl
    field_names = {f.name for f in dataclasses.fields(ReferenceControl)}
    assert "execution_binding" not in field_names
    assert "admitted" not in field_names
    print("[PASS] test_atlas_has_no_execution_authority_surface")


def test_existing_stage_a_ingestion_unaffected():
    """The 75-test regression baseline's most load-bearing single function
    (ingest_stage_a_observation) must still work exactly as before -- this
    Atlas addition must not have touched it."""
    from serum2.source.visual_evidence import VisualEvidenceBundle
    from serum2.producer.visual_reasoner import ingest_stage_a_observation

    bundle = VisualEvidenceBundle(source_url="https://example.com/x", source_id="x", video_id="x")
    data = {
        "stage_a_provenance": {"observer": "claude_code", "observation_mode": "direct_visual_inspection", "model_api_used": False},
        "frames": [{
            "frame_id": "f1", "timestamp_sec": 1.0, "serum_visible": True,
            "controls": [{"control_id": "env1.release", "control_type": "knob", "value": "15 ms", "status": "OBSERVED", "confidence": 0.9}],
            "mod_routes": [], "unknown": [],
        }],
    }
    ingest_stage_a_observation(bundle, data)
    assert bundle.reasoning_error is None
    assert len(bundle.ui_state_snapshots) == 1
    assert bundle.ui_state_snapshots[0].controls[0].control_id == "env1.release"
    print("[PASS] test_existing_stage_a_ingestion_unaffected")


if __name__ == "__main__":
    test_atlas_version_identity()
    test_canonical_ids_are_stable_across_calls()
    test_no_duplicate_canonical_ids()
    test_aliases_resolve_to_one_canonical_control()
    test_reference_default_state_is_not_episode_evidence()
    test_atlas_has_no_execution_authority_surface()
    test_existing_stage_a_ingestion_unaffected()
    print("\nAll Serum Reference Atlas tests passed.")
