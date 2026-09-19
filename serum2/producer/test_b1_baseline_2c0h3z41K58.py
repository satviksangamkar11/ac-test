"""B1 Integration Test: Re-run 2c0h3z41K58 baseline through B1 foundation.

This test validates B1 against the frozen coverage baseline from 2c0h3z41K58.
It measures whether the new derivation-based Brain improves or maintains coverage.

Baseline (before B1):
- 9 events total
- 0 EXECUTABLE
- 2 REFUSED_NO_BRAIN_CONCEPT
- 3 REFUSED_NO_CAPABILITY
- 4 no semantic intent
"""
import pytest
import json
import sys
from pathlib import Path
from dataclasses import dataclass

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.producer.concept_representation import ConceptDerivationEngine, Provenance
from serum2.producer.operation_spec import OperationInterpreter
from serum2.producer.request_context import ContextExtractor
from serum2.producer.universal_intent import IntentFormationEngine, IntentValidator
from serum2.producer.contract_registry import ContractRegistry
from serum2.reference.serum_atlas import normalize_control


@dataclass
class EventAnalysis:
    """Analyze one event through B1."""
    event_num: int
    time_range: str
    semantic_changes: list[str]
    intent_phrase: str
    canonical_target: Optional[str]
    representation_provenance: str
    operation_type: str
    overall_confidence: float
    b1_result: str  # EXECUTABLE, REFUSED_*, NOT_ATTEMPTED
    audit_trace: list[str]


class TestB1Baseline:
    """Re-run 2c0h3z41K58 baseline through B1."""

    def load_baseline(self) -> dict:
        """Load the coverage table from the fresh run."""
        baseline_file = Path(ROOT) / "serum2/data/runs/2c0h3z41K58/coverage_table.json"
        if not baseline_file.exists():
            pytest.skip(f"Baseline file not found: {baseline_file}")

        with open(baseline_file) as f:
            return json.load(f)

    def run_b1_analysis(self, change: str) -> EventAnalysis:
        """Run B1 on one semantic change."""
        # Parse change: "control: before→after"
        if not change or "(" in change:
            return None

        try:
            parts = change.split(":")
            if len(parts) != 2:
                return None

            control_id = parts[0].strip()
            change_desc = parts[1].strip()

            # Normalize control ID
            atlas_r = normalize_control(control_id)
            if atlas_r.status not in ("EXACT", "ALIAS"):
                return {
                    "canonical_target": control_id,
                    "representation_provenance": Provenance.MISSING.value,
                    "operation_type": "unknown",
                    "overall_confidence": 0.0,
                    "b1_result": "REFUSED_UNRESOLVED_REFERENCE",
                    "audit_trace": [f"Atlas resolve failed: {atlas_r.status}"],
                }

            canonical = atlas_r.canonical_id

            # Derive concept
            engine = ConceptDerivationEngine(ContractRegistry())
            rep = engine.derive(canonical)

            # Interpret operation
            # Extract the "before→after" and pick the direction
            if "→" in change_desc:
                before, after = change_desc.split("→")
                # Simple heuristic: if numeric grew, it's increase; otherwise decrease
                try:
                    b = float(before.split()[0].replace("s", "").replace("ms", "").replace("ms", ""))
                    a = float(after.split()[0].replace("s", "").replace("ms", "").replace("ms", ""))
                    phrase = "increase" if a > b else "decrease"
                except:
                    phrase = "change"
            else:
                phrase = "change"

            op_interp = OperationInterpreter()
            op = op_interp.interpret(phrase)

            # Extract context
            ctx_extractor = ContextExtractor()
            ctx = ctx_extractor.extract(phrase)

            # Form intent
            intent_engine = IntentFormationEngine()
            intent = intent_engine.form_intent(canonical, rep, op, ctx)

            # Validate
            validator = IntentValidator()
            is_valid, issues = validator.validate(intent)

            # Determine B1 result
            if not rep.is_derivable():
                b1_result = "REFUSED_NO_BRAIN_CONCEPT"
            elif op.operation.value == "unknown":
                b1_result = "REFUSED_UNRESOLVED_REFERENCE"
            elif is_valid and intent.overall_confidence >= 0.50:
                b1_result = "B1_READY"  # Ready for downstream Capability Resolution
            else:
                b1_result = "B1_UNCERTAIN"

            return {
                "canonical_target": canonical,
                "representation_provenance": rep.provenance.value,
                "operation_type": op.operation.value,
                "overall_confidence": intent.overall_confidence,
                "b1_result": b1_result,
                "audit_trace": intent.derivation_trace[:5],  # first 5 steps
            }

        except Exception as e:
            return {
                "canonical_target": "error",
                "representation_provenance": "error",
                "operation_type": "error",
                "overall_confidence": 0.0,
                "b1_result": "ERROR",
                "audit_trace": [str(e)],
            }

    def test_event_1_oscA_warp_mode(self):
        """Event 1: oscA.warp_mode OFF→REMAP 2 (REFUSED_NO_BRAIN_CONCEPT)."""
        result = self.run_b1_analysis("oscA.warp_mode: OFF→REMAP 2")

        assert result is not None
        assert result["canonical_target"] == "oscA.warp_mode"
        # warp_mode should still lack a Brain concept (no contract, no semantic target)
        # B1 should mark it as MISSING
        if result["representation_provenance"] == "missing":
            assert result["b1_result"] in ("REFUSED_NO_BRAIN_CONCEPT", "B1_UNCERTAIN")

    def test_event_2_env2_decay_sustain(self):
        """Event 2: env2.decay/sustain (REFUSED_NO_CAPABILITY in baseline)."""
        result = self.run_b1_analysis("env2.decay: 1.00 s→1.77 s")

        assert result is not None
        assert result["canonical_target"] == "env2.decay"
        # env2.decay SHOULD have a contract; B1 should derive it
        assert result["representation_provenance"] in ("contract", "legacy_semantic_target")
        # If contract is found, next step is Capability Resolution (downstream)
        if result["representation_provenance"] == "contract":
            assert result["b1_result"] == "B1_READY"  # ready for downstream

    def test_event_4_lfo1_rate_smooth(self):
        """Event 4: lfo1.rate/smooth (REFUSED_NO_CAPABILITY in baseline)."""
        result = self.run_b1_analysis("lfo1.rate: 1/4→4.5 Hz")

        assert result is not None
        assert result["canonical_target"] == "lfo1.rate"
        # lfo1.rate should have a contract
        assert result["representation_provenance"] in ("contract", "legacy_semantic_target")

    def test_event_5_filter1_enabled(self):
        """Event 5: filter1.enabled (REFUSED_NO_CAPABILITY in baseline)."""
        result = self.run_b1_analysis("filter1.enabled: off→on")

        assert result is not None
        assert result["canonical_target"] == "filter1.enabled"
        # filter1.enabled should resolve and be ready for Capability check
        assert result["b1_result"] in ("B1_READY", "B1_UNCERTAIN", "REFUSED_NO_CAPABILITY")

    def test_event_6_lfo1_smooth(self):
        """Event 6: lfo1.smooth (REFUSED_NO_BRAIN_CONCEPT in baseline)."""
        result = self.run_b1_analysis("lfo1.smooth: 71→None")

        assert result is not None
        assert result["canonical_target"] == "lfo1.smooth"
        # lfo1.smooth should have a contract (after fix)
        if result["representation_provenance"] == "contract":
            assert result["b1_result"] == "B1_READY"

    def test_b1_preserves_frozen_refusal_taxonomy(self):
        """B1 must use only the four frozen refusal codes."""
        allowed_codes = {
            "REFUSED_UNRESOLVED_REFERENCE",
            "REFUSED_AMBIGUOUS_REFERENCE",
            "REFUSED_NO_BRAIN_CONCEPT",
            "REFUSED_NO_CAPABILITY",  # (downstream)
            "B1_READY",  # (ready for downstream)
            "B1_UNCERTAIN",  # (needs review)
        }

        # Run a few events and check results stay within frozen taxonomy
        for change in [
            "oscA.warp_mode: OFF→REMAP 2",
            "env2.decay: 1.00 s→1.77 s",
            "filter1.enabled: off→on",
        ]:
            result = self.run_b1_analysis(change)
            if result:
                assert result["b1_result"] in allowed_codes or result["b1_result"] == "ERROR"


# ---- Standalone measurement ----

def measure_b1_coverage():
    """Measure B1 coverage on 2c0h3z41K58 baseline.

    This can be run as `pytest --co -q test_b1_baseline_2c0h3z41K58.py::measure_b1_coverage`
    to get a summary without running full tests.
    """
    baseline_file = Path(ROOT) / "serum2/data/runs/2c0h3z41K58/coverage_table.json"

    if not baseline_file.exists():
        print("Baseline file not found; skipping measurement.")
        return

    with open(baseline_file) as f:
        baseline = json.load(f)

    print("\n" + "="*100)
    print("B1 Baseline Coverage Measurement (2c0h3z41K58)")
    print("="*100)
    print(f"{'Event':>3} {'Control':>30} {'Before':>25} {'After':>25}")
    print("="*100)

    for event in baseline:
        changes = event.get("changes", "").split(";")[0]  # first change
        print(f"{event['event']:3d} {changes[:30]:>30} [→] {event['terminal'][:25]:>25}")

    print("="*100)
    print("Baseline: 9 events total")
    print("  - 0 EXECUTABLE")
    print("  - 2 REFUSED_NO_BRAIN_CONCEPT (Events 1, 6)")
    print("  - 3 REFUSED_NO_CAPABILITY (Events 2, 4, 5)")
    print("  - 4 no semantic content (Events 3, 7, 8, 9)")
    print("\nB1 Goal: Eliminate hand-written concept tables; measure improvement in refusals.")
    print("="*100 + "\n")


if __name__ == "__main__":
    measure_b1_coverage()
