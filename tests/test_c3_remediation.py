"""C3 Architecture Remediation: deterministic tests for GAP A/B/C fixes.

No Qwen API calls, no Serum, no DawDreamer. Pure policy-layer logic tests.

GAP A — Identity binding: control_id propagated through policy; mismatched
         candidates filtered; all-mismatch -> IDENTITY_UNRESOLVED.
GAP B — Corroboration required: single source (any confidence) -> AMBIGUOUS.
         Only multi-source agreement -> OBSERVED.
GAP C — Evidence provenance: evidence_hash propagated to OBSERVED result.

None of these changes touch the mutation pipeline (Gate A/B, A2 admission,
epoch enforcement, authorized-operation creation, compiler validation).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from serum2.producer.observation_policy import (
    ObservationCandidate, adjudicate,
    OUTCOME_CANDIDATE, OUTCOME_OBSERVED, OUTCOME_AMBIGUOUS, OUTCOME_UNREADABLE,
    OUTCOME_IDENTITY_UNRESOLVED, CONFIDENT_THRESHOLD,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _cand(value, confidence=0.95, source="vlm", control_id="", evidence_hash=None,
          outcome=OUTCOME_CANDIDATE):
    return ObservationCandidate(
        outcome=outcome, value=value, confidence=confidence, source=source,
        control_id=control_id, evidence_hash=evidence_hash,
    )


# ── Scenario 1: GAP B — single high-confidence source is AMBIGUOUS, not OBSERVED ──

def test_s1_single_high_confidence_is_ambiguous():
    """Single source above CONFIDENT_THRESHOLD must return AMBIGUOUS (GAP B fix)."""
    r = adjudicate([_cand(1.5, confidence=0.95)])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.single_source is True
    assert r.value == 1.5


# ── Scenario 2: GAP B — single source at exactly CONFIDENT_THRESHOLD ──

def test_s2_single_at_threshold_is_ambiguous():
    """Single source exactly at threshold must still be AMBIGUOUS."""
    r = adjudicate([_cand(1.0, confidence=CONFIDENT_THRESHOLD)])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.single_source is True


# ── Scenario 3: GAP B — single source below threshold stays AMBIGUOUS ──

def test_s3_single_below_threshold_is_ambiguous():
    """Single source below threshold: still AMBIGUOUS (behavior unchanged)."""
    r = adjudicate([_cand(1.0, confidence=0.4)])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.single_source is True


# ── Scenario 4: multi-source agreement still produces OBSERVED ──

def test_s4_multi_source_agreement_is_observed():
    """Two independent sources agreeing -> OBSERVED (multi-source path unchanged)."""
    r = adjudicate([_cand(5.0, source="vlm"), _cand(5.0, source="ocr")])
    assert r.outcome == OUTCOME_OBSERVED
    assert r.value == 5.0
    assert r.single_source is False


# ── Scenario 5: multi-source disagreement stays AMBIGUOUS ──

def test_s5_multi_source_disagreement_is_ambiguous():
    """Two sources disagreeing -> AMBIGUOUS (unchanged)."""
    r = adjudicate([_cand(5.0, source="vlm"), _cand(8.0, source="ocr")])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.value is None


# ── Scenario 6: GAP A — control_id propagated on OBSERVED result ──

def test_s6_control_id_propagated_on_observed():
    """After GAP A fix, OBSERVED result carries control_id from candidates."""
    r = adjudicate([
        _cand(5.0, source="vlm", control_id="env2.decay"),
        _cand(5.0, source="ocr", control_id="env2.decay"),
    ], requested_control_id="env2.decay")
    assert r.outcome == OUTCOME_OBSERVED
    assert r.control_id == "env2.decay"


# ── Scenario 7: GAP A — identity mismatch candidate filtered out ──

def test_s7_identity_mismatch_candidate_filtered():
    """Candidate with wrong control_id is excluded; remaining single source
    returns AMBIGUOUS (single source corroboration required)."""
    good = _cand(5.0, source="vlm", control_id="env2.decay")
    bad = _cand(1.0, source="ocr", control_id="env1.decay")  # wrong control
    r = adjudicate([good, bad], requested_control_id="env2.decay")
    # bad candidate is filtered; only good remains; single source -> AMBIGUOUS
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.single_source is True
    assert r.value == 5.0


# ── Scenario 8: GAP A — all candidates identity-mismatch -> IDENTITY_UNRESOLVED ──

def test_s8_all_identity_mismatch_returns_identity_unresolved():
    """When all candidates have non-empty mismatching control_id, return
    IDENTITY_UNRESOLVED (not UNREADABLE) so callers can distinguish the cases."""
    r = adjudicate([
        _cand(1.0, source="vlm", control_id="env1.decay"),
        _cand(1.0, source="ocr", control_id="env1.decay"),
    ], requested_control_id="env2.decay")
    assert r.outcome == OUTCOME_IDENTITY_UNRESOLVED
    assert r.control_id == "env2.decay"


# ── Scenario 9: GAP A — no identity assertion (empty control_id) passes through ──

def test_s9_empty_control_id_candidate_not_filtered():
    """Candidates without a control_id asserted (empty string) are not filtered
    even when requested_control_id is set — identity check only applies to
    explicitly tagged candidates."""
    r = adjudicate([
        _cand(5.0, source="vlm", control_id=""),   # no identity asserted
        _cand(5.0, source="ocr", control_id=""),   # no identity asserted
    ], requested_control_id="env2.decay")
    assert r.outcome == OUTCOME_OBSERVED


# ── Scenario 10: GAP C — evidence_hash propagated to OBSERVED result ──

def test_s10_evidence_hash_propagated_on_observed():
    """GAP C fix: OBSERVED result carries evidence_hash from the highest-confidence
    agreeing candidate."""
    r = adjudicate([
        _cand(5.0, source="vlm", confidence=0.94, evidence_hash="abc123"),
        _cand(5.0, source="ocr", confidence=0.91, evidence_hash="def456"),
    ])
    assert r.outcome == OUTCOME_OBSERVED
    # highest-confidence candidate is vlm (0.94); its hash propagates
    assert r.evidence_hash == "abc123"


# ── Scenario 11: GAP C — evidence_hash on AMBIGUOUS single-source ──

def test_s11_evidence_hash_on_single_source_ambiguous():
    """Single-source AMBIGUOUS result also carries the evidence_hash for
    diagnostic purposes."""
    r = adjudicate([_cand(5.0, source="vlm", confidence=0.95, evidence_hash="crop_sha")])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.evidence_hash == "crop_sha"


# ── Scenario 12: empty candidates -> UNREADABLE (unchanged) ──

def test_s12_empty_candidates_returns_unreadable():
    """Empty candidate list -> UNREADABLE (baseline unchanged)."""
    r = adjudicate([])
    assert r.outcome == OUTCOME_UNREADABLE


# ── Mutation boundary assertion ───────────────────────────────────────────────

def test_mutation_boundary_observation_policy_not_imported_by_gate_modules():
    """observation_policy.py must NOT be imported by state_admission,
    authorized_state_compiler, or gate_b_certificate. These gate modules must
    remain independent of the observation layer."""
    import importlib
    import types

    gate_modules = [
        "serum2.producer.state_admission",
        "serum2.execution.authorized_state_compiler",
        "serum2.producer.gate_b_certificate",
    ]
    for mod_name in gate_modules:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        for attr in dir(mod):
            obj = getattr(mod, attr, None)
            if isinstance(obj, types.ModuleType):
                assert "observation_policy" not in obj.__name__, (
                    "%s imports observation_policy — mutation boundary violated" % mod_name
                )
