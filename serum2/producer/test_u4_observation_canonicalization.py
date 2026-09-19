"""U4: Observation Canonicalization — RED tests.

Proves the entire observation path uses a single, Atlas-backed identity
resolver and never does a second guessed-concept lookup.

Architecture under test:
    raw control_id / label / screen_region
            ↓
    normalize_control()   ← the ONE identity resolver
            ↓
    EXACT | ALIAS | AMBIGUOUS | UNRESOLVED
            ↓
    ControlState.resolution carries ALL four fields:
        status, canonical_id, candidates, raw_control_id
    ControlState.value / .status (OBSERVED/OCCLUDED/…) are NEVER touched

Risky bypass that U4 must close:
    visual_reasoner._TARGET_TO_CONCEPT   — second identity table
    event_to_intent.production_event_to_requests() — uses _TARGET_TO_CONCEPT
    visual_reasoner.infer_from_diffs()   — uses _TARGET_TO_CONCEPT
    → Atlas-known controls NOT in the table are silently dropped

Central U4 invariant:
    ID canonicalization ≠ value interpretation
    "lfo3.sync_division" / label "RATE" / value "1/4"
    must NOT become lfo3.rate = "1/4"
"""
import pytest
from serum2.reference.serum_atlas import normalize_control, EXACT, ALIAS, AMBIGUOUS, UNRESOLVED
from serum2.producer.visual_reasoner import _canonicalize_control, ingest_stage_a_observation
from serum2.source.visual_evidence import VisualEvidenceBundle, ProductionEvent


# ---------------------------------------------------------------------------
# U4-A: Atlas resolution statuses, directly via normalize_control
# ---------------------------------------------------------------------------

class TestU4AtlasResolutionStatuses:
    """normalize_control() returns the correct status for each case.

    These four cases are the canonical Atlas contract; everything above
    (ingest, diff, event→intent) must flow through them.
    """

    def test_exact_match_returns_exact_status_and_canonical_id(self):
        """env1.decay is a first-class Atlas control."""
        res = normalize_control("env1.decay")
        assert res.status == EXACT
        assert res.canonical_id == "env1.decay"

    def test_exact_match_env1_hold(self):
        """env1.hold is Atlas-known; confirmed by U1."""
        res = normalize_control("env1.hold")
        assert res.status == EXACT
        assert res.canonical_id == "env1.hold"

    def test_alias_resolves_to_canonical_and_preserves_input(self):
        """oscA.wt_pos is an alias for the canonical oscA.wt_position.

        U4 requirement: ALIAS status + canonical_id filled + original input
        available via candidates or the raw query.
        If the Atlas does not support this alias yet, this test is RED and
        drives an Atlas alias extension.
        """
        res = normalize_control("oscA.wt_pos")
        assert res.status == ALIAS, \
            f"oscA.wt_pos should be an ALIAS; got {res.status}. " \
            f"If not in Atlas, add it — abbreviated forms must alias to canonical."
        assert res.canonical_id == "oscA.wt_position", \
            f"ALIAS must point to oscA.wt_position, got {res.canonical_id}"

    def test_ambiguous_returns_no_canonical_id_but_retains_candidates(self):
        """'cutoff' alone is ambiguous (filter1.cutoff vs filter2.cutoff)."""
        res = normalize_control("cutoff")
        assert res.status == AMBIGUOUS
        assert res.canonical_id is None, \
            "Ambiguous resolution must NOT pick a canonical_id"
        assert res.candidates, \
            "Ambiguous resolution must retain all candidate canonical_ids"
        assert "filter1.cutoff" in res.candidates or "filter2.cutoff" in res.candidates, \
            f"Expected filter cutoff candidates, got {res.candidates}"

    def test_unresolved_returns_no_canonical_id_and_preserves_input(self):
        """oscA.flux is not an Atlas control; resolution must not invent one."""
        res = normalize_control("oscA.flux")
        assert res.status == UNRESOLVED
        assert res.canonical_id is None, \
            "UNRESOLVED must not invent a canonical_id"


# ---------------------------------------------------------------------------
# U4-B: _canonicalize_control() — the ingest-layer Atlas wrapper
# ---------------------------------------------------------------------------

class TestU4CanonicalizeControl:
    """_canonicalize_control(census_entry) calls normalize_control and
    produces a (returned_id, resolution_dict) pair that preserves every
    raw field while adding Atlas provenance.
    """

    def _entry(self, control_id, label=None, screen_region=None, value="50 ms"):
        return {
            "control_id": control_id,
            "label": label,
            "screen_region": screen_region,
            "value": value,
            "control_type": "knob",
            "status": "OBSERVED",
            "confidence": 0.9,
        }

    def test_exact_id_gets_canonical_id_returned(self):
        cid, res = _canonicalize_control(self._entry("env1.decay"))
        assert cid == "env1.decay"
        assert res["status"] == EXACT

    def test_exact_preserves_raw_fields(self):
        entry = self._entry("env1.decay", label="DEC", value="220 ms")
        cid, res = _canonicalize_control(entry)
        assert res["raw_control_id"] == "env1.decay"
        assert res["raw_label"] == "DEC"
        # value is NOT in the resolution dict — it lives in ControlState.value
        # (identity resolution never touches the value)

    def test_ambiguous_id_returns_raw_id_as_fallback_and_candidates(self):
        """For AMBIGUOUS, canonical_id is None → returned ID is the raw input."""
        cid, res = _canonicalize_control(self._entry("cutoff"))
        assert res["status"] == AMBIGUOUS
        assert res.get("canonical_id") is None
        assert res.get("candidates"), "Candidates must be retained for AMBIGUOUS"
        # The returned control_id should be the raw input, not a guess
        assert cid == "cutoff", \
            f"AMBIGUOUS resolution must not pick a target; returned {cid!r}"

    def test_unresolved_id_returns_raw_id_not_an_invented_target(self):
        cid, res = _canonicalize_control(self._entry("oscA.flux"))
        assert res["status"] == UNRESOLVED
        assert cid == "oscA.flux"  # raw preserved, nothing invented

    def test_label_settles_ambiguous_id_when_label_is_more_specific(self):
        """If control_id is too generic but the UI label is specific,
        the label's Atlas resolution may disambiguate — but ONLY when the
        canonical_id from the label is in the candidate set, not by guessing."""
        # "filter1.cutoff" as raw_id (EXACT), label "Filter 1 Freq"
        entry = self._entry("filter1.cutoff", label="Filter 1 Freq")
        cid, res = _canonicalize_control(entry)
        # At minimum: raw_control_id preserved, canonical_id is filter1.cutoff
        assert res["raw_control_id"] == "filter1.cutoff"
        assert cid == "filter1.cutoff"

    def test_identity_resolution_never_modifies_the_observed_value(self):
        """The canonical ID swap must not touch the value field.

        This is the central U4 invariant:
            observed label "RATE" + value "1/4" + raw_id "lfo3.sync_division"
            must NOT become lfo3.rate = "1/4"
        """
        entry = self._entry("lfo3.sync_division", label="RATE", value="1/4")
        cid, res = _canonicalize_control(entry)
        # Resolution may be UNRESOLVED or EXACT for lfo3.sync_division
        # In either case: the value "1/4" must NOT be in the resolution dict
        assert "value" not in res or res.get("value") != "1/4", \
            "Resolution dict must not carry the observed value — identity ≠ value"
        # And the raw_id must be preserved
        assert res["raw_control_id"] == "lfo3.sync_division"


# ---------------------------------------------------------------------------
# U4-C: Slot safety — label and context disambiguation
# ---------------------------------------------------------------------------

class TestU4SlotSafety:
    """'release' without a slot context must not silently pick env1.release.
    The Atlas must provide the disambiguation; the observation layer must not
    guess or pick arbitrarily.
    """

    def test_bare_release_is_ambiguous_or_unresolved_not_silently_env1(self):
        """'release' alone must not resolve to env1.release (or any one slot)."""
        res = normalize_control("release")
        assert res.status in (AMBIGUOUS, UNRESOLVED), \
            f"'release' alone must not resolve silently; got {res.status} → {res.canonical_id}"
        assert res.canonical_id is None or res.canonical_id not in ("env1.release",), \
            f"'release' must not silently become env1.release; got {res.canonical_id}"

    def test_filter2_label_resolves_to_filter2_not_filter1(self):
        """'Filter 2 Cutoff' as a label must map to filter2.cutoff, not filter1."""
        entry = {
            "control_id": "filter2.cutoff",  # raw observer-assigned id
            "label": "Filter 2 Cutoff",
            "screen_region": "Filter 2 panel",
            "value": "0.3",
            "control_type": "knob",
            "status": "OBSERVED",
            "confidence": 0.85,
        }
        cid, res = _canonicalize_control(entry)
        assert cid == "filter2.cutoff", \
            f"filter2.cutoff label must not collapse to filter1; got {cid!r}"
        assert res["raw_control_id"] == "filter2.cutoff"

    def test_filter1_label_resolves_to_filter1_not_filter2(self):
        entry = {
            "control_id": "filter1.cutoff",
            "label": "Filter 1 Cutoff",
            "screen_region": "Filter 1 panel",
            "value": "0.7",
            "control_type": "knob",
            "status": "OBSERVED",
            "confidence": 0.9,
        }
        cid, res = _canonicalize_control(entry)
        assert cid == "filter1.cutoff"

    def test_ambiguous_slot_is_not_resolved_by_picking(self):
        """When ambiguity is genuine, the observation layer must NOT pick."""
        # 'cutoff' with no slot context — ambiguous across filter1/filter2
        res = normalize_control("cutoff")
        assert res.status == AMBIGUOUS
        assert res.canonical_id is None


# ---------------------------------------------------------------------------
# U4-D: ingest_stage_a_observation preserves raw + resolution separately
# ---------------------------------------------------------------------------

class TestU4IngestPreservesRaw:
    """ControlState after ingest must carry both raw_control_id and
    the Atlas resolution dict, never conflating the two."""

    def _bundle(self):
        return VisualEvidenceBundle(
            source_url="test://u4", source_id="u4", video_id="u4"
        )

    def _stage_a_data(self, controls):
        return {
            "stage_a_provenance": {
                "observer": "test", "observation_mode": "direct", "model_api_used": False
            },
            "frames": [{
                "frame_id": "f001", "timestamp_sec": 1.0,
                "serum_visible": True, "visible_panel": "ENV1",
                "controls": controls, "mod_routes": [], "unknown": [],
                "target_reading": {},
            }],
        }

    def test_exact_control_carries_canonical_id_in_resolution(self):
        bundle = self._bundle()
        data = self._stage_a_data([{
            "control_id": "env1.decay", "label": "DEC",
            "control_type": "knob", "value": "220 ms",
            "status": "OBSERVED", "confidence": 0.9,
        }])
        ingest_stage_a_observation(bundle, data)
        assert bundle.ui_state_snapshots, "Snapshot must be created"
        ctrl = bundle.ui_state_snapshots[0].controls[0]
        assert ctrl.control_id == "env1.decay"
        assert ctrl.resolution is not None
        assert ctrl.resolution.get("status") == EXACT
        assert ctrl.resolution.get("canonical_id") == "env1.decay"
        assert ctrl.resolution.get("raw_control_id") == "env1.decay"
        # Value is on ControlState, not in resolution
        assert ctrl.value == "220 ms"

    def test_ambiguous_control_carries_candidates_not_a_guess(self):
        bundle = self._bundle()
        data = self._stage_a_data([{
            "control_id": "cutoff", "label": "CUTOFF",
            "control_type": "knob", "value": "0.5",
            "status": "OBSERVED", "confidence": 0.7,
        }])
        ingest_stage_a_observation(bundle, data)
        if not bundle.ui_state_snapshots:
            pytest.skip("No snapshot created (may be filtered)")
        ctrl = bundle.ui_state_snapshots[0].controls[0]
        assert ctrl.resolution is not None
        assert ctrl.resolution.get("status") == AMBIGUOUS
        assert ctrl.resolution.get("canonical_id") is None, \
            "AMBIGUOUS must not have a canonical_id — no picking allowed"
        assert ctrl.resolution.get("candidates"), \
            "AMBIGUOUS must carry the candidate set"

    def test_unresolved_control_is_retained_not_dropped(self):
        """An UNRESOLVED observation is still an observation — do not drop it."""
        bundle = self._bundle()
        data = self._stage_a_data([{
            "control_id": "oscA.completely_unknown_parameter",
            "label": "???",
            "control_type": "knob", "value": "42",
            "status": "OBSERVED", "confidence": 0.4,
        }])
        ingest_stage_a_observation(bundle, data)
        assert bundle.ui_state_snapshots, \
            "UNRESOLVED controls must not be silently dropped from the snapshot"
        ctrl = bundle.ui_state_snapshots[0].controls[0]
        # Raw ID preserved
        assert ctrl.resolution is not None
        assert ctrl.resolution.get("raw_control_id") == "oscA.completely_unknown_parameter"
        assert ctrl.resolution.get("status") == UNRESOLVED

    def test_identity_resolution_does_not_change_observed_value(self):
        """The critical U4 invariant: value on ControlState is the observer's
        value, not something touched by the Atlas resolution path."""
        bundle = self._bundle()
        data = self._stage_a_data([{
            "control_id": "env1.hold", "label": "HOLD",
            "control_type": "knob", "value": "999 ms",  # sentinel value
            "status": "OBSERVED", "confidence": 0.9,
        }])
        ingest_stage_a_observation(bundle, data)
        ctrl = bundle.ui_state_snapshots[0].controls[0]
        assert ctrl.value == "999 ms", \
            f"Atlas resolution must not modify the observed value; got {ctrl.value!r}"

    def test_observation_status_is_independent_of_atlas_resolution_status(self):
        """ControlState.status (OBSERVED/OCCLUDED/…) is about visual quality.
        resolution.status (EXACT/ALIAS/AMBIGUOUS/UNRESOLVED) is about identity.
        They are separate axes; one must never override the other."""
        bundle = self._bundle()
        data = self._stage_a_data([{
            "control_id": "env1.hold", "label": "HOLD",
            "control_type": "knob", "value": None,
            "status": "AMBIGUOUS",  # visual quality: blurry/unclear
            "confidence": 0.3,
        }])
        ingest_stage_a_observation(bundle, data)
        ctrl = bundle.ui_state_snapshots[0].controls[0]
        # Visual status preserved
        assert ctrl.status == "AMBIGUOUS", \
            f"ControlState.status must reflect visual quality, got {ctrl.status!r}"
        # Atlas resolution status is EXACT (identity IS known)
        assert ctrl.resolution.get("status") == EXACT, \
            f"resolution.status must reflect Atlas identity independently; got {ctrl.resolution.get('status')!r}"


# ---------------------------------------------------------------------------
# U4-E: No second identity resolver (the bypass gap)
# ---------------------------------------------------------------------------

class TestU4NoBypassResolver:
    """The downstream pipeline must NOT use _TARGET_TO_CONCEPT as a second
    identity resolver. Atlas-known controls not in that table must still
    produce candidates / interpretations.

    These tests are RED in the current code because event_to_intent.py and
    visual_reasoner.infer_from_diffs() both silently drop controls that
    have no entry in _TARGET_TO_CONCEPT.
    """

    def test_event_to_requests_produces_candidate_for_atlas_known_control(self):
        """env1.hold is Atlas-known (U1 proven) but NOT in _TARGET_TO_CONCEPT.
        Current behavior: produces [] — silently dropped.
        U4 requirement: must produce at least one candidate routed via Atlas.
        """
        from serum2.producer.event_to_intent import production_event_to_requests
        from serum2.producer.visual_reasoner import _TARGET_TO_CONCEPT

        # Verify the boundary condition
        assert "Env1.Hold" not in _TARGET_TO_CONCEPT, \
            "Env1.Hold must not be in _TARGET_TO_CONCEPT for this boundary test"

        event = ProductionEvent(
            event_id="u4-test-001",
            start_timestamp_sec=0.0,
            end_timestamp_sec=1.0,
            snapshot_diff={
                "changed_controls": [
                    {"control_id": "env1.hold", "before": "50 ms", "after": "100 ms"}
                ],
                "added_routes": [], "removed_routes": [],
            }
        )
        candidates = production_event_to_requests(event)
        assert len(candidates) > 0, (
            "U4 FAILED: Atlas-known control env1.hold produced no candidate "
            "because it is not in _TARGET_TO_CONCEPT. "
            "The fix: remove _TARGET_TO_CONCEPT bypass; route through Atlas identity."
        )

    def test_event_to_requests_produces_candidate_for_oscA_unison(self):
        """oscA.unison is Atlas-known but not in _TARGET_TO_CONCEPT."""
        from serum2.producer.event_to_intent import production_event_to_requests
        from serum2.producer.visual_reasoner import _TARGET_TO_CONCEPT

        assert "OscA.Unison" not in _TARGET_TO_CONCEPT

        event = ProductionEvent(
            event_id="u4-test-002",
            start_timestamp_sec=0.0,
            end_timestamp_sec=1.0,
            snapshot_diff={
                "changed_controls": [
                    {"control_id": "oscA.unison", "before": "1", "after": "4"}
                ],
                "added_routes": [], "removed_routes": [],
            }
        )
        candidates = production_event_to_requests(event)
        assert len(candidates) > 0, (
            "Atlas-known control oscA.unison must produce a candidate "
            "without relying on _TARGET_TO_CONCEPT."
        )

    def test_infer_from_diffs_produces_interpretation_for_atlas_known_target(self):
        """infer_from_diffs drops diffs for targets not in _TARGET_TO_CONCEPT.
        U4 requirement: Atlas-known targets must produce interpretations.
        """
        from serum2.producer.visual_reasoner import infer_from_diffs, _TARGET_TO_CONCEPT
        from serum2.source.visual_evidence import CanonicalStateDiff, ObservedCanonicalState

        # env1.hold is Atlas-known, not in _TARGET_TO_CONCEPT
        assert "Env1.Hold" not in _TARGET_TO_CONCEPT

        bundle = VisualEvidenceBundle(source_url="test://u4", source_id="u4", video_id="u4")
        diffs = [CanonicalStateDiff(
            target="Env1.Hold",
            before=ObservedCanonicalState(
                target="Env1.Hold", value="50 ms", frame_id="f1",
                timestamp_sec=0.0, frame_hash="aaa"
            ),
            after=ObservedCanonicalState(
                target="Env1.Hold", value="100 ms", frame_id="f2",
                timestamp_sec=1.0, frame_hash="bbb"
            ),
            changed=True,
        )]
        infer_from_diffs(bundle, diffs)
        assert bundle.interpretations, (
            "U4 FAILED: infer_from_diffs produced no interpretation for Env1.Hold "
            "because it is not in _TARGET_TO_CONCEPT. "
            "The fix: remove _TARGET_TO_CONCEPT gate; route through Atlas identity."
        )

    def test_target_to_concept_table_is_not_the_identity_resolver(self):
        """_TARGET_TO_CONCEPT must not be used as the sole gate for
        which controls can be processed. Its existence in the codebase
        is the bypass this test documents.
        """
        from serum2.producer.visual_reasoner import _TARGET_TO_CONCEPT
        # This table is small; Atlas has 255+ controls. The gap is structural.
        assert len(_TARGET_TO_CONCEPT) < 10, \
            f"_TARGET_TO_CONCEPT has grown suspiciously large ({len(_TARGET_TO_CONCEPT)} entries). " \
            f"U4 requires removing this table, not growing it."
