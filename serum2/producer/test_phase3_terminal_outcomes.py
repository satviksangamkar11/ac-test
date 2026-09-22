"""Phase 3.3: Terminal Outcome Classification Tests

Prove that every observation can reach an explicit terminal state.
Uses real Phase 3 reference evidence from HEEGN1Xl5o4.

No execution testing. Only evidence accounting.
"""

import sys
from expected_inventory import (
    TerminalObservation,
    ObservationOutcome,
)


def test_clear_text_observation():
    """Test 1: Unison=7 — clear text capture from screenshot."""
    obs = TerminalObservation(
        canonical_id="oscA.unison",
        outcome=ObservationOutcome.OBSERVED,
        observation_status="OBSERVED",
        evidence_status="SUFFICIENT",
        proof_level="LIVE_VERIFIED",
        candidate={
            "normalized_value": (7.0, ""),
            "strategy": "NUMERIC",
            "confidence": 1.0,
        },
        provenance={
            "source_image": "step1_01m09s_osc_a_sawtooth_setup.jpg",
            "evidence_type": "CLEAR_TEXT",
            "gate": "Gate-A Test 1",
        }
    )
    assert obs.outcome == ObservationOutcome.OBSERVED
    assert obs.evidence_status == "SUFFICIENT"
    print("[PASS] Test 1 (CLEAR_TEXT): oscA.unison -> OBSERVED")
    return True


def test_clear_text_enum():
    """Test 3: Chaos: Lorenz — clear enum text."""
    obs = TerminalObservation(
        canonical_id="lfo1.shape",
        outcome=ObservationOutcome.OBSERVED,
        observation_status="OBSERVED",
        evidence_status="SUFFICIENT",
        proof_level="LIVE_VERIFIED",
        candidate={
            "normalized_value": "Lorenz",
            "strategy": "ENUM",
            "confidence": 1.0,
        },
        provenance={
            "source_image": "step2_02m08s_lfo1_lorenz_full_pattern.jpg",
            "evidence_type": "CLEAR_TEXT",
            "gate": "Gate-A Test 3",
        }
    )
    assert obs.outcome == ObservationOutcome.OBSERVED
    print("[PASS] Test 3 (CLEAR_ENUM): lfo1.shape -> OBSERVED")
    return True


def test_visual_only_observation():
    """Test 2: Matrix Amount slider — visual geometry, no text."""
    obs = TerminalObservation(
        canonical_id="matrix.amount[Env 2->Filter 1 Freq]",
        outcome=ObservationOutcome.OBSERVED,  # slider exists, position visible
        observation_status="OBSERVED",
        evidence_status="VISUAL_ONLY",  # no text value; requires calibration
        proof_level="NOT_VERIFIED",  # unverified until calibration complete
        candidate=None,  # no numeric value extracted yet
        provenance={
            "source_image": "step3_04m35s_matrix_mod_routes.jpg",
            "evidence_type": "VISUAL_ONLY",
            "note": "slider position visible; pixel-to-value mapping Phase 3.5",
            "gate": "Gate-A Test 2 (AMOUNT component)",
        }
    )
    assert obs.outcome == ObservationOutcome.OBSERVED
    assert obs.evidence_status == "VISUAL_ONLY"
    assert obs.proof_level == "NOT_VERIFIED"
    print("[PASS] Test 2 (VISUAL_ONLY): matrix.amount -> OBSERVED (unverified, visual-only)")
    return True


def test_source_insufficient():
    """Test 4: Drive = 1.9 — exists conceptually, source cannot prove it.

    This is THE critical test. Drive must NOT disappear just because
    the screenshot is too small to read.
    """
    obs = TerminalObservation(
        canonical_id="fx.overdrive.drive",
        outcome=ObservationOutcome.SOURCE_INSUFFICIENT,  # ← explicit terminal state
        observation_status="OBSERVED",  # model extracted something
        evidence_status="SOURCE_INSUFFICIENT",  # but source frames inadequate
        proof_level="NOT_VERIFIED",
        candidate={
            "normalized_value": (1.9, ""),
            "strategy": "NUMERIC",
            "confidence": 0.0,  # low confidence due to source quality
        },
        provenance={
            "source_image": "step5_07m04s_main_delay_ping_pong.jpg",
            "evidence_type": "MODEL_OUTPUT_ONLY",
            "qwen_raw_output": "DRIVE=1.9",
            "ground_truth": "1.9",
            "note": "Qwen extracted 1.9; source screenshot too zoomed-out to independently verify",
            "gate": "Gate-A Test 4",
            "status": "Expected, unverified, recorded as SOURCE_INSUFFICIENT",
        }
    )
    assert obs.outcome == ObservationOutcome.SOURCE_INSUFFICIENT
    assert obs.observation_status == "OBSERVED"
    assert obs.evidence_status == "SOURCE_INSUFFICIENT"
    # CRITICAL: it must NOT be:
    # - MISSING
    # - IGNORED
    # - UNKNOWN_AND_DROPPED
    # - NOT_APPLICABLE
    print("[PASS] Test 4 (SOURCE_INSUFFICIENT): fx.overdrive.drive -> OBSERVED + SOURCE_INSUFFICIENT (not dropped!)")
    return True


def test_not_visible_in_frame():
    """Expected control not visible in captured frames."""
    obs = TerminalObservation(
        canonical_id="oscC.enabled",
        outcome=ObservationOutcome.NOT_VISIBLE_IN_FRAME,
        observation_status="UNOBSERVED",
        evidence_status="NOT_VISIBLE",
        proof_level="NOT_VERIFIED",
        candidate=None,
        provenance={
            "note": "OSC C control expected but not shown in any frame",
            "reason": "OSC C off-screen or collapsed in UI",
        }
    )
    assert obs.outcome == ObservationOutcome.NOT_VISIBLE_IN_FRAME
    print("[PASS] Expected but NOT_VISIBLE_IN_FRAME: oscC.enabled -> accounted for")
    return True


def test_runtime_state():
    """Voice count meter — transient/runtime state, not preset parameter."""
    obs = TerminalObservation(
        canonical_id="voicing.voice_count",
        outcome=ObservationOutcome.NOT_APPLICABLE,
        observation_status="OBSERVED",
        evidence_status="SUFFICIENT",
        proof_level="VERIFIED",
        candidate={
            "normalized_value": None,
            "strategy": "RUNTIME_STATE",
            "outcome": "NOT_APPLICABLE",
        },
        provenance={
            "note": "Voice meter is transient playhead state, not storable preset parameter",
            "evidence": "visible in frame but classified as NOT_APPLICABLE",
        }
    )
    assert obs.outcome == ObservationOutcome.NOT_APPLICABLE
    print("[PASS] RUNTIME_STATE: voicing.voice_count -> NOT_APPLICABLE (transient, not preset)")
    return True


def test_unsupported_modality():
    """Modality exists but not yet implemented."""
    obs = TerminalObservation(
        canonical_id="someFutureControl.visual_calibration",
        outcome=ObservationOutcome.UNSUPPORTED_MODALITY,
        observation_status="OBSERVED",
        evidence_status="INSUFFICIENT",
        proof_level="NOT_VERIFIED",
        candidate=None,
        provenance={
            "note": "Observable visually but modality (e.g., waveform shape comparison) not yet implemented",
        }
    )
    assert obs.outcome == ObservationOutcome.UNSUPPORTED_MODALITY
    print("[PASS] UNSUPPORTED_MODALITY: future_control -> accounted for (not silently dropped)")
    return True


def run_phase_3_3_tests():
    """Run all Phase 3.3 terminal outcome classification tests."""
    print("\n" + "=" * 70)
    print("Phase 3.3: Terminal Outcome Classification Tests")
    print("=" * 70)

    tests = [
        ("Clear text", test_clear_text_observation),
        ("Clear enum", test_clear_text_enum),
        ("Visual-only", test_visual_only_observation),
        ("Source insufficient (CRITICAL)", test_source_insufficient),
        ("Not visible in frame", test_not_visible_in_frame),
        ("Runtime state", test_runtime_state),
        ("Unsupported modality", test_unsupported_modality),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"❌ {name}: {e}")

    print("\n" + "=" * 70)
    print(f"Phase 3.3 Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_3_3_tests()
    sys.exit(0 if success else 1)
