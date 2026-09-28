"""Regression tests for the VLM/OCR -> Stage-A production-pipeline gap closed this round.

Branch archaeology found zero lost/abandoned work: every VLM/OCR/observation-engine/Qwen-ROI
commit across all 67 remote branches was already merged into this branch's history (confirmed
via `git log HEAD..origin/<branch>` returning 0 for every one of them). The real gap was NOT
missing code -- it was four concrete, generic, reproducible bugs in the code that already
existed, each verified directly against source (not assumed from a report) before being fixed:

1. serum2/producer/expected_inventory.py: normalize_control() returns a Resolution object
   (status, canonical_id, candidates, raw), never a plain string. resolve_observation_type()
   (formerly ExpectedInventoryBuilder._resolve_observation_type) passed that Resolution object
   directly into get_control(control_id: str), which silently returns None for a non-matching
   dict key (no exception) -- so this function returned (None, None) — "cannot resolve" — for
   EVERY control, unconditionally, since it was written. Fixed: use resolution.canonical_id,
   and only trust an EXACT/ALIAS resolution.

2. serum2/producer/universal_frame_observer.py's _adjudicate(): hardcoded every observed
   control through {"element_kind": "CONTROL", "control_type": "continuous"} regardless of
   what the control actually is -- forcing every toggle/enum/route through NUMERIC parsing,
   where it could never produce a valid CANDIDATE. Fixed: resolve the real Atlas-derived
   strategy per control_id (reusing fix #1's resolve_observation_type(), not a second
   hardcoded copy) and pass it via force_strategy.

3. universal_frame_observer.py's to_metrics_json(): NUMERIC strategy's normalized_value is
   (num, unit); _flatten_value() kept only num, silently discarding the unit c3_observation_
   metrics.json downstream consumers need to build a correct state_ledger.Row.

4. serum2/pipeline/runner.py: _stage_ledger/_stage_admission/_stage_compile called
   `derive(control_id, value)` -- state_ledger.derive()'s real signature is
   `derive(row: Row, tempo) -> None` (mutates in place, returns None). Every call site caught
   the resulting AttributeError with a bare `except Exception: pass`, so LEDGER always produced
   zero rows regardless of what OBSERVATION found. A second bug in the same function:
   admit_rows() mutates its input Row objects in place and returns a SEPARATE list of plain
   diagnostic dicts (keyed "status", not "admission") -- _stage_compile passed that dict list
   into ops_from_rows() (which needs real Row objects), and _stage_admission's admitted_count
   read a key ("admission") that dict never has, so it was always 0 -- which made
   _stage_compile refuse to even attempt compilation regardless of real admission outcomes.

Together these four bugs meant: even with perfect VLM/OCR accuracy, ZERO observations could
ever reach a real ledger row, admission, or compiled preset through the automated pipeline.
Fixing accuracy alone (a separate, already-partially-addressed problem -- see qwen_ui_findings.txt
and five_roi_test_results.json for the documented free-frame vs. targeted-ROI-crop findings)
would have changed nothing while these bugs stood.

Scope note: this does NOT touch the already-complete 330-control mapping/contract work, and
does NOT attempt full ExpectedInventory-driven completeness enforcement for arbitrary videos
(that needs a generic transcript/vision -> expected-control-set derivation that does not yet
exist anywhere in this repo's history; a real remaining limitation, reported honestly rather
than faked).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from serum2.producer.expected_inventory import resolve_observation_type
from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.state_ledger import Row, derive
from serum2.producer.state_admission import admit_rows
from serum2.execution.authorized_state_compiler import ops_from_rows, compile_ops


class TestResolveObservationTypeAtlasBug:
    """Bug 1: normalize_control() returns a Resolution, not a string."""

    def test_real_numeric_control_resolves_correctly(self):
        obs_kind, strategy = resolve_observation_type("env1.attack")
        assert (obs_kind, strategy) == ("NUMERIC", "NUMERIC")

    def test_real_control_via_alias_also_resolves(self):
        obs_kind, strategy = resolve_observation_type("env2.decay")
        assert (obs_kind, strategy) == ("NUMERIC", "NUMERIC")

    def test_unresolvable_control_id_returns_none_none(self):
        obs_kind, strategy = resolve_observation_type("no.such.control.exists.anywhere")
        assert (obs_kind, strategy) == (None, None)

    def test_does_not_crash_on_any_string(self):
        # A pure regression guard: this must never raise, whatever garbage is passed.
        for garbage in ("", "   ", "!!!", "a" * 500):
            obs_kind, strategy = resolve_observation_type(garbage)
            assert obs_kind is None and strategy is None


class TestAdjudicateUsesRealStrategyNotHardcodedNumeric:
    """Bug 2: _adjudicate() forced every control through NUMERIC regardless of real kind."""

    def test_universal_frame_observer_imports_resolve_observation_type(self):
        import inspect
        import serum2.producer.universal_frame_observer as ufo
        assert '"element_kind": "CONTROL"' not in inspect.getsource(ufo)
        assert '"control_type": "continuous"' not in inspect.getsource(ufo)
        assert "resolve_observation_type" in inspect.getsource(ufo)

    def test_adjudicate_marks_unresolvable_control_unreadable_not_numeric(self):
        from serum2.producer.universal_frame_observer import FrameObservationCensus, RawFinding, ResolvedFinding

        census = FrameObservationCensus()
        raw = RawFinding(frame_id="f1", group_index=0, claimed_panel="", claimed_label="",
                         raw_value="7", source_type="vlm", vlm_confidence=0.95, evidence_hash="h1")
        resolved = [ResolvedFinding(raw=raw, resolved_control_id="no.such.control.exists", resolution_status="EXACT")]

        result = census._adjudicate(resolved, groups=[], engine=None)
        assert "no.such.control.exists" in result
        assert result["no.such.control.exists"].outcome == "UNREADABLE"


class TestMetricsPreserveUnit:
    """Bug 3: to_metrics_json() discarded the unit half of a NUMERIC (num, unit) value."""

    def test_flatten_and_unit_extraction(self):
        from serum2.producer.universal_frame_observer import _flatten_value, _value_unit

        assert _flatten_value((5.0, "s")) == 5.0
        assert _value_unit((5.0, "s")) == "s"
        assert _flatten_value("Chaos: Lorenz") == "Chaos: Lorenz"
        assert _value_unit("Chaos: Lorenz") is None
        assert _value_unit(True) is None

    def test_to_metrics_json_includes_adjudicated_unit_field(self):
        from serum2.producer.universal_frame_observer import ObservationCensus
        from serum2.producer.observation_policy import ObservationCandidate as PC, OUTCOME_OBSERVED

        census = ObservationCensus()
        census.adjudicated = {
            "env1.attack": PC(outcome=OUTCOME_OBSERVED, value=(5.0, "s"), confidence=0.9,
                              source="vlm", evidence_hash="h1"),
        }
        metrics = census.to_metrics_json()["metrics"]
        assert len(metrics) == 1
        assert metrics[0]["adjudicated_value"] == 5.0
        assert metrics[0]["adjudicated_unit"] == "s"


class TestRunnerRowFromMetricReplacesBrokenDeriveCalls:
    """Bug 4: runner.py called derive(control_id, value) -- wrong signature, always AttributeError,
    always silently swallowed to zero rows."""

    def test_real_derive_signature_is_row_and_tempo(self):
        import inspect
        assert list(inspect.signature(derive).parameters) == ["row", "tempo"]

    def test_calling_derive_the_old_broken_way_raises(self):
        with pytest.raises(AttributeError):
            derive("env1.attack", 5.0)  # the exact call runner.py used to make

    def test_row_from_metric_builds_a_real_row_and_derives_correctly(self):
        from serum2.pipeline.runner import _row_from_metric

        metric = {"control_id": "env1.attack", "adjudicated_value": 5.0, "adjudicated_unit": "s",
                  "timestamp_sec": 12.5}
        row = _row_from_metric(metric)
        assert row is not None
        assert row.terminal == "OPERATION_DERIVED"
        assert row.control_id == "env1.attack"
        assert row.op["value"] == 5.0

    def test_route_kind_metric_is_skipped_not_mis_called(self):
        from serum2.pipeline.runner import _row_from_metric

        metric = {"control_id": "route:lfo1->filter1.cutoff", "adjudicated_value": None,
                  "adjudicated_unit": None, "timestamp_sec": 0.0}
        assert _row_from_metric(metric) is None

    def test_unresolvable_control_returns_none_not_a_fabricated_row(self):
        from serum2.pipeline.runner import _row_from_metric

        metric = {"control_id": "no.such.control.exists", "adjudicated_value": 5.0,
                  "adjudicated_unit": "s", "timestamp_sec": 0.0}
        assert _row_from_metric(metric) is None


class TestRunnerFullChainFromRealMetricsToCompiledPreset:
    """End to end: a real c3_observation_metrics.json-shaped metric list survives
    LEDGER -> ADMISSION -> COMPILE the way runner.py's fixed stages now do it."""

    def test_env1_attack_metric_reaches_compile_ops_success(self, tmp_path, monkeypatch):
        from serum2.pipeline.runner import _row_from_metric

        monkeypatch.setenv("SERUM_PRESETS_PATH", str(tmp_path))
        metrics = [
            {"control_id": "env1.attack", "adjudicated_outcome": "OBSERVED",
             "adjudicated_value": 5.0, "adjudicated_unit": "s", "timestamp_sec": 3.0},
        ]
        rows = [r for r in (_row_from_metric(m) for m in metrics) if r is not None]
        assert len(rows) == 1

        epoch = EPOCH_2_0_23
        admit_rows(rows, epoch=epoch,
                  binding_evidence_dir="parameter_characterization/binding_evidence",
                  promoted_evidence_dir="parameter_characterization/binding_evidence_mcp_exec_v1")
        admitted_rows_only = [r for r in rows if r.admission == "ADMITTED"]
        assert admitted_rows_only, "env1.attack must be admitted under the real 2.0.23 evidence"

        ops = ops_from_rows(admitted_rows_only, epoch)
        report = compile_ops(ops, "test", "runner.py chain regression", epoch)
        assert report.status == "SUCCESS"
        assert report.spec["envelopes"] == [{"attack": 5.0}]

    def test_admit_rows_returned_dicts_key_is_status_not_admission(self):
        """Bug 4b: the returned per-row dict uses key "status", matching Row.admission's
        value -- never a key literally named "admission"."""
        row = Row(control_id="env1.attack", value=5.0, unit="s", status="OBSERVED",
                  control_type="control", source_ts=0.0, n_readings=1, changed_from_previous=False,
                  context={})
        derive(row, tempo=None)
        result = admit_rows([row], EPOCH_2_0_23,
                            binding_evidence_dir="parameter_characterization/binding_evidence",
                            promoted_evidence_dir="parameter_characterization/binding_evidence_mcp_exec_v1")
        assert len(result) == 1
        assert "admission" not in result[0]
        assert result[0]["status"] == "ADMITTED"
        assert result[0]["status"] == row.admission


# ---------------------------------------------------------------------------
# ROI value-extraction wiring (this round): observe_control_in_frame(), the proven
# locate -> crop -> transcribe -> explicit-UNREADABLE mechanism (existed, unused by
# production), is now what _adjudicate() actually reads per candidate temporal group --
# never the full-frame census's own guessed value. Real Qwen/EasyOCR need a GPU + local
# model weights this container does not have; every test here drives the REAL adjudication
# logic (strategy dispatch, corroboration, provenance, fail-closed behavior) through an
# injected fake engine, exactly the seam _adjudicate()'s new `engine` parameter exists for.
# Validating the fake engine's canned answers against a REAL video is Local's job, not this
# pass's -- this proves the wiring and policy are correct, not model accuracy.
# ---------------------------------------------------------------------------

class _FakeEngine:
    """Test double for ObservationEngine: canned observe_control_in_frame() results keyed by
    (frame_path, control_id), so tests drive _adjudicate()'s real corroboration/provenance
    logic without a GPU or downloaded model weights."""

    def __init__(self, answers=None, raises_for=frozenset()):
        # answers: {(frame_path, control_id): ObservationCandidate}
        self._answers = answers or {}
        self._raises_for = raises_for

    def observe_control_in_frame(self, frame_path, control_id):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        key = (frame_path, control_id)
        if key in self._raises_for:
            raise RuntimeError("simulated malformed model output for %r" % (key,))
        return self._answers.get(key, PC(outcome="UNREADABLE", control_id=control_id))


def _finding(frame_id, group_index, evidence_hash="h"):
    from serum2.producer.universal_frame_observer import RawFinding
    return RawFinding(frame_id=frame_id, group_index=group_index, claimed_panel="", claimed_label="",
                      raw_value="irrelevant-full-frame-guess", source_type="vlm", vlm_confidence=0.9,
                      evidence_hash=evidence_hash)


def _group(group_index, representative_frame_id, representative_path):
    from serum2.producer.universal_frame_observer import TemporalGroup
    return TemporalGroup(group_index=group_index, frame_ids=[representative_frame_id],
                         representative_frame_id=representative_frame_id, representative_path=representative_path,
                         start_ts=0.0, end_ts=0.0, mean_change_score=0.0)


class TestROIValueExtractionWiredIntoProduction:
    """Proves the real production _adjudicate() path performs ROI value extraction, per the
    W2 next-step spec's items A-J."""

    def test_A_correct_numeric_value_via_two_group_corroboration(self):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg"), _group(1, "f1", "/frames/g1.jpg")]
        engine = _FakeEngine(answers={
            ("/frames/g0.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(5.0, "s"), confidence=0.92,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack",
                                                  evidence_hash="roi_g0"),
            ("/frames/g1.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(5.0, "s"), confidence=0.88,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack",
                                                  evidence_hash="roi_g1"),
        })
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="env1.attack", resolution_status="EXACT"),
                   ResolvedFinding(raw=_finding("f1", 1), resolved_control_id="env1.attack", resolution_status="EXACT")]

        census = FrameObservationCensus()
        result = census._adjudicate(resolved, groups, engine)

        assert result["env1.attack"].outcome == "OBSERVED"
        assert result["env1.attack"].value == (5.0, "s")

    def test_B_correct_enum_value(self):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg"), _group(1, "f1", "/frames/g1.jpg")]
        engine = _FakeEngine(answers={
            ("/frames/g0.jpg", "filter1.type"): PC(outcome="CANDIDATE", value="lowpass_24", confidence=1.0,
                                                    source="qwen2.5-vl-3b-instruct", control_id="filter1.type",
                                                    evidence_hash="roi_g0"),
            ("/frames/g1.jpg", "filter1.type"): PC(outcome="CANDIDATE", value="lowpass_24", confidence=1.0,
                                                    source="qwen2.5-vl-3b-instruct", control_id="filter1.type",
                                                    evidence_hash="roi_g1"),
        })
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="filter1.type", resolution_status="EXACT"),
                   ResolvedFinding(raw=_finding("f1", 1), resolved_control_id="filter1.type", resolution_status="EXACT")]

        census = FrameObservationCensus()
        result = census._adjudicate(resolved, groups, engine)

        assert result["filter1.type"].outcome == "OBSERVED"
        assert result["filter1.type"].value == "lowpass_24"

    def test_C_correct_boolean_enable_state(self):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg"), _group(1, "f1", "/frames/g1.jpg")]
        engine = _FakeEngine(answers={
            ("/frames/g0.jpg", "oscA.enabled"): PC(outcome="CANDIDATE", value="ON", confidence=1.0,
                                                    source="qwen2.5-vl-3b-instruct", control_id="oscA.enabled",
                                                    evidence_hash="roi_g0"),
            ("/frames/g1.jpg", "oscA.enabled"): PC(outcome="CANDIDATE", value="ON", confidence=1.0,
                                                    source="qwen2.5-vl-3b-instruct", control_id="oscA.enabled",
                                                    evidence_hash="roi_g1"),
        })
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="oscA.enabled", resolution_status="EXACT"),
                   ResolvedFinding(raw=_finding("f1", 1), resolved_control_id="oscA.enabled", resolution_status="EXACT")]

        census = FrameObservationCensus()
        result = census._adjudicate(resolved, groups, engine)

        assert result["oscA.enabled"].outcome == "OBSERVED"
        assert result["oscA.enabled"].value == "ON"

    def test_D_explicit_unreadable_never_fabricates_a_value(self):
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg")]
        engine = _FakeEngine(answers={})  # default UNREADABLE for any key
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="env1.attack", resolution_status="EXACT")]

        census = FrameObservationCensus()
        result = census._adjudicate(resolved, groups, engine)

        assert result["env1.attack"].outcome == "UNREADABLE"
        assert result["env1.attack"].value is None

    def test_E_malformed_model_output_fails_closed_not_crash(self):
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg")]
        engine = _FakeEngine(raises_for={("/frames/g0.jpg", "env1.attack")})
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="env1.attack", resolution_status="EXACT")]

        census = FrameObservationCensus()
        result = census._adjudicate(resolved, groups, engine)  # must not raise

        assert result["env1.attack"].outcome == "UNREADABLE"

    def test_F_conflicting_values_are_not_silently_accepted(self):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg"), _group(1, "f1", "/frames/g1.jpg")]
        engine = _FakeEngine(answers={
            ("/frames/g0.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(5.0, "s"), confidence=0.9,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack"),
            ("/frames/g1.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(8.0, "s"), confidence=0.9,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack"),
        })
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="env1.attack", resolution_status="EXACT"),
                   ResolvedFinding(raw=_finding("f1", 1), resolved_control_id="env1.attack", resolution_status="EXACT")]

        census = FrameObservationCensus()
        result = census._adjudicate(resolved, groups, engine)

        # A hallucinated/conflicting reading must never resolve to OBSERVED just because
        # something was returned -- the split-vote policy path (unchanged GAP B) applies.
        assert result["env1.attack"].outcome == "AMBIGUOUS"
        assert result["env1.attack"].value is None

    def test_G_roi_provenance_survives_to_the_adjudicated_result_and_metrics(self):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding, ObservationCensus

        groups = [_group(0, "f0", "/frames/g0.jpg"), _group(1, "f1", "/frames/g1.jpg")]
        engine = _FakeEngine(answers={
            ("/frames/g0.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(5.0, "s"), confidence=0.9,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack",
                                                  evidence_hash="real_roi_sha256_g0"),
            ("/frames/g1.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(5.0, "s"), confidence=0.9,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack",
                                                  evidence_hash="real_roi_sha256_g1"),
        })
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="env1.attack", resolution_status="EXACT"),
                   ResolvedFinding(raw=_finding("f1", 1), resolved_control_id="env1.attack", resolution_status="EXACT")]

        census_obj = FrameObservationCensus()
        adjudicated = census_obj._adjudicate(resolved, groups, engine)

        # The propagated evidence_hash must be a real ROI crop's hash, never the full-frame's.
        assert adjudicated["env1.attack"].evidence_hash in ("real_roi_sha256_g0", "real_roi_sha256_g1")

        census = ObservationCensus()
        census.adjudicated = adjudicated
        metrics = census.to_metrics_json()["metrics"]
        assert metrics[0]["evidence_hash"] in ("real_roi_sha256_g0", "real_roi_sha256_g1")
        assert metrics[0]["adjudicated_unit"] == "s"

    def test_H_temporal_corroboration_confirms_a_value_single_group_does_not(self):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        # Single group only -> AMBIGUOUS (single_source), never OBSERVED, even at high confidence.
        groups_one = [_group(0, "f0", "/frames/g0.jpg")]
        engine = _FakeEngine(answers={
            ("/frames/g0.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(5.0, "s"), confidence=0.99,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack"),
        })
        resolved_one = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="env1.attack", resolution_status="EXACT")]
        census = FrameObservationCensus()
        result_one = census._adjudicate(resolved_one, groups_one, engine)
        assert result_one["env1.attack"].outcome == "AMBIGUOUS"
        assert result_one["env1.attack"].single_source is True

    def test_I_contradictory_observations_are_deterministic_across_repeat_runs(self):
        from serum2.producer.observation_policy import ObservationCandidate as PC
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg"), _group(1, "f1", "/frames/g1.jpg")]
        engine = _FakeEngine(answers={
            ("/frames/g0.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(5.0, "s"), confidence=0.9,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack"),
            ("/frames/g1.jpg", "env1.attack"): PC(outcome="CANDIDATE", value=(8.0, "s"), confidence=0.9,
                                                  source="qwen2.5-vl-3b-instruct", control_id="env1.attack"),
        })
        resolved = [ResolvedFinding(raw=_finding("f0", 0), resolved_control_id="env1.attack", resolution_status="EXACT"),
                   ResolvedFinding(raw=_finding("f1", 1), resolved_control_id="env1.attack", resolution_status="EXACT")]

        outcomes = set()
        for _ in range(5):
            census = FrameObservationCensus()
            result = census._adjudicate(resolved, groups, engine)
            outcomes.add(result["env1.attack"].outcome)
        assert outcomes == {"AMBIGUOUS"}, "adjudication must be deterministic, not flaky, across repeat runs"

    def test_J_no_observation_disappears_silently(self):
        """A control the full-frame census claimed in a group, whose ROI read comes back
        UNREADABLE, must still get an explicit terminal entry in the results dict -- never
        silently absent."""
        from serum2.producer.universal_frame_observer import FrameObservationCensus, ResolvedFinding

        groups = [_group(0, "f0", "/frames/g0.jpg")]
        engine = _FakeEngine(answers={})  # every ROI read comes back UNREADABLE
        resolved = [
            ResolvedFinding(raw=_finding("f0", 0, "h1"), resolved_control_id="env1.attack", resolution_status="EXACT"),
            ResolvedFinding(raw=_finding("f0", 0, "h2"), resolved_control_id="oscA.enabled", resolution_status="EXACT"),
        ]

        census = FrameObservationCensus()
        result = census._adjudicate(resolved, groups, engine)

        assert set(result.keys()) == {"env1.attack", "oscA.enabled"}
        assert all(r.outcome == "UNREADABLE" for r in result.values())


class TestFrameConservationUnaffectedByROIWiring:
    """Step 5: every decoded source frame remains accounted for regardless of VLM/OCR/ROI
    outcome -- ingestion (Stage 1) is independent of adjudication (Stage 7)."""

    def test_every_manifest_frame_is_ingested_regardless_of_adjudication_outcome(self, tmp_path):
        from serum2.producer.universal_frame_observer import FrameObservationCensus

        manifest = {"frames": [
            {"frame_id": "f_%d" % i, "timestamp_sec": float(i), "artifact_path": "nonexistent_%d.jpg" % i,
             "artifact_hash": "h%d" % i}
            for i in range(12)
        ]}
        engine = _FakeEngine(answers={})  # everything UNREADABLE
        census = FrameObservationCensus(engine=engine)
        result = census.run(manifest, run_dir=tmp_path)

        assert result.total_frames == 12
        assert len(result.frame_records) == 12
        # Missing image files -> NO_IMAGE, still explicitly accounted for, never dropped.
        assert all(r.pixel_status == "NO_IMAGE" for r in result.frame_records)
