#!/usr/bin/env python3
"""
Regression Test: Golden Production-Slice Fixture

Validates that the frozen ep_prod_001 episode:
  - All 11 provenance fields present and intact
  - No corrupted/missing data
  - Artifacts and hashes unchanged
  - Outcome still PASS

Single gate before advancing to Ableton integration (Gate 2).
"""

import sys
import json
from pathlib import Path

ROOT = str(Path(__file__).parent.parent)
sys.path.insert(0, ROOT)

from golden_fixture import GOLDEN_FIXTURE, load_evidence_record, validate_golden_fixture


def test_golden_fixture_11_point_provenance():
    """Test: All 11 provenance points present and immutable."""

    print("=" * 80)
    print("TEST: Golden Production-Slice Fixture — 11-Point Provenance")
    print("=" * 80)

    evidence = load_evidence_record()

    print("\n[Step 1] Verify all 11 provenance fields present")

    required_fields = [
        "episode_id",
        "episode_intent_text",
        "semantic_decision",
        "admitted_capability_ids",
        "preset_spec",
        "mcp_invocation",
        "preset_path",
        "preset_sha256",
        "serum_load_status",
        "measurements",
        "outcome",
    ]

    for i, field in enumerate(required_fields, start=1):
        if field not in evidence:
            print(f"[FAIL] Provenance point {i}: Missing field '{field}'")
            return False
        print(f"[OK] {i}. {field}")

    print("\n[Step 2] Validate immutable fixture values")

    try:
        validate_golden_fixture()
        print("[OK] All fixture values verified against golden reference")
    except AssertionError as e:
        print(f"[FAIL] Fixture validation failed: {e}")
        return False

    print("\n[Step 3] Verify outcome is PASS")

    if evidence["outcome"] != "PASS":
        print(f"[FAIL] Outcome is '{evidence['outcome']}', expected 'PASS'")
        return False

    print(f"[OK] Outcome: {evidence['outcome']}")

    print("\n[Step 4] Verify artifacts are valid (no None/empty)")

    checks = [
        ("preset_path", evidence.get("preset_path")),
        ("preset_sha256", evidence.get("preset_sha256")),
        ("serum_load_status", evidence.get("serum_load_status")),
        ("measurements.rms_db", evidence.get("measurements", {}).get("rms_db")),
        ("measurements.peak_db", evidence.get("measurements", {}).get("peak_db")),
        ("measurements.spectral_centroid_hz", evidence.get("measurements", {}).get("spectral_centroid_hz")),
    ]

    for name, value in checks:
        if value is None or (isinstance(value, str) and not value):
            print(f"[FAIL] {name} is empty or None")
            return False
        print(f"[OK] {name}: {value if isinstance(value, str) else f'{value:.1f}'}")

    print("\n[Step 5] Verify measurement tolerances passed")

    meas = evidence["measurements"]
    deltas = evidence["measurement_deltas"]

    tolerance_checks = [
        ("RMS", deltas["rms_db"], GOLDEN_FIXTURE.rms_tolerance),
        ("Peak", deltas["peak_db"], GOLDEN_FIXTURE.peak_tolerance),
        ("Centroid", deltas["spectral_centroid_hz"], GOLDEN_FIXTURE.centroid_tolerance),
    ]

    for name, delta, tolerance in tolerance_checks:
        if abs(delta) <= tolerance:
            print(f"[OK] {name}: delta {delta:+.1f} within +/- {tolerance}")
        else:
            print(f"[FAIL] {name}: delta {delta:+.1f} exceeds +/- {tolerance}")
            return False

    return True


def main():
    """Run regression test."""

    success = test_golden_fixture_11_point_provenance()

    print("\n" + "=" * 80)

    if success:
        print("[OK] REGRESSION TEST PASSED")
        print("\nGolden Production-Slice Fixture (ep_prod_001) is frozen and reproducible.")
        print("Ready for Gate 2: Ableton Integration")
        print("=" * 80)
        return 0
    else:
        print("[FAIL] REGRESSION TEST FAILED")
        print("Golden fixture is corrupted or incomplete.")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
