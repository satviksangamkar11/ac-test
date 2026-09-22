"""Phase 2 regression test: 5 Gate-A crops through new observation engine.

Verifies that the new ObservationEngine preserves behavior for known test cases.
"""
import json
from pathlib import Path
from observation_engine import ObservationEngine


def test_gate_a_regression():
    """Run 5 Gate-A test cases through observation engine."""
    engine = ObservationEngine()

    # Load ground truth from gate_b_manifest
    manifest_path = Path(__file__).parent.parent.parent / "gate_b_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    test_cases = [
        {
            "name": "Test 1: OSC A Unison",
            "control_id": "oscA.unison",
            "element_kind": "CONTROL",
            "control_type": "continuous",
            "raw_value": "7",
            "unit": None,
            "expected_normalized": (7.0, ""),
            "strategy": "NUMERIC",  # Unison is numeric
        },
        {
            "name": "Test 2: Matrix Route",
            "control_id": "route:Env 2->Filter 1 Freq",
            "element_kind": "ROUTE",
            "control_type": "route",
            "raw_value": "Env 2",
            "expected_normalized": "Env 2",
            "strategy": "ROUTE_TEXT",
        },
        {
            "name": "Test 3: LFO1 Mode",
            "control_id": "lfo1.shape",
            "element_kind": "SELECTOR",
            "control_type": "enum",
            "raw_value": "Lorenz",  # Enum value only, not the "Chaos: " prefix
            "enum_values": ["Rossler", "Lorenz", "RandomSH", "Path"],
            "expected_normalized": "Lorenz",
            "strategy": "ENUM",
        },
        {
            "name": "Test 4: Drive Numeric",
            "control_id": "fx.overdrive.drive",
            "element_kind": "CONTROL",
            "control_type": "continuous",
            "raw_value": "1.9",
            "unit": None,
            "expected_normalized": (1.9, ""),
            "strategy": "NUMERIC",
        },
        {
            "name": "Test 5: Legato Boolean",
            "control_id": "voicing.legato",
            "element_kind": "ENABLE_STATE",
            "control_type": "toggle",
            "raw_value": "OFF",
            "expected_normalized": "OFF",
            "strategy": "ENABLE_STATE",
        },
    ]

    results = []
    for tc in test_cases:
        context = {
            "control_id": tc["control_id"],
            "element_kind": tc["element_kind"],
            "control_type": tc["control_type"],
            "unit": tc.get("unit"),
            "enum_values": tc.get("enum_values", []),
            "vlm_source": False,  # These are direct reads, not Qwen
        }

        candidate = engine.observe(tc["raw_value"], context)

        # Verify strategy selection
        assert candidate.strategy == tc["strategy"], f"{tc['name']}: strategy mismatch. Expected {tc['strategy']}, got {candidate.strategy}"

        # Verify normalized value
        if isinstance(tc["expected_normalized"], tuple):
            # Numeric: (value, unit)
            assert isinstance(candidate.normalized_value, tuple), f"{tc['name']}: expected tuple, got {type(candidate.normalized_value)}"
            assert candidate.normalized_value[0] == tc["expected_normalized"][0], f"{tc['name']}: value mismatch"
        else:
            # Text/enum/state
            assert candidate.normalized_value == tc["expected_normalized"], \
                f"{tc['name']}: normalized value mismatch. Expected {tc['expected_normalized']}, got {candidate.normalized_value}"

        results.append({
            "test": tc["name"],
            "control_id": tc["control_id"],
            "strategy": candidate.strategy,
            "normalized": candidate.normalized_value,
            "confidence": candidate.confidence,
            "passed": True,
        })
        print(f"[PASS] {tc['name']}: {candidate.strategy} -> {candidate.normalized_value} (confidence={candidate.confidence})")

    print(f"\nPhase 2 Regression: {len(results)}/5 PASSED")
    return all(r["passed"] for r in results)


if __name__ == "__main__":
    success = test_gate_a_regression()
    exit(0 if success else 1)
