"""Gate B operand boundary regression tests.

Verifies that the qualification_test_value (0.5 for env2.decay) can NEVER become
the production mutation operand, and that requested values 3.0 / 5.0 / 8.0 all
produce distinct plan qualification_test_value that doesn't substitute for them.

Also verifies machine-checkable Gate B certificate semantics (cloud-side, no native
Serum required — uses mock ProducerResult to exercise the certificate logic).
"""
import inspect
import pytest
from pathlib import Path

from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest, ProducerResult

BINDING_DIR = Path(__file__).parent.parent / "serum2" / "qualification" / "binding_evidence"
PROMOTED_DIR = Path(__file__).parent.parent / "parameter_characterization" / "binding_evidence_mcp_exec_v1"


def _brain():
    return ProducerBrain(epoch=EPOCH_2_0_23,
                         binding_evidence_dir=str(BINDING_DIR),
                         promoted_evidence_dir=str(PROMOTED_DIR))


# ---------------------------------------------------------------------------
# F4 regression: requested value must not be replaced by qualification_test_value
# ---------------------------------------------------------------------------

class TestOperandBoundary:
    """qualification_test_value is evidence metadata — never the production operand."""

    @pytest.mark.parametrize("requested_value", [3.0, 5.0, 8.0])
    def test_plan_contains_no_mutation_value_used_key(self, requested_value):
        """The old key 'mutation_value_used' must not appear in the plan (renamed to
        qualification_test_value to prevent callers confusing it for the operand)."""
        brain = _brain()
        result = brain.execute(ProducerRequest(
            user_intent="set Env2.Decay to %.1f seconds" % requested_value,
            semantic_target="Env2.Decay"))
        plan = getattr(result, "_serum_preset_plan", None)
        assert plan is not None
        assert "mutation_value_used" not in plan, (
            "Plan must not expose 'mutation_value_used' — renamed to "
            "'qualification_test_value' to prevent ambiguity. requested=%.1f, plan keys=%r"
            % (requested_value, list(plan.keys())))

    @pytest.mark.parametrize("requested_value", [3.0, 5.0, 8.0])
    def test_qualification_test_value_is_present_and_not_requested(self, requested_value):
        """qualification_test_value is metadata about the binding test; it must
        differ from the requested production value for all three test values."""
        brain = _brain()
        result = brain.execute(ProducerRequest(
            user_intent="set Env2.Decay to %.1f seconds" % requested_value,
            semantic_target="Env2.Decay"))
        plan = getattr(result, "_serum_preset_plan", None)
        assert plan is not None
        qtv = plan.get("qualification_test_value")
        assert qtv is not None, "qualification_test_value must be in plan"
        assert qtv != requested_value, (
            "qualification_test_value %r must differ from requested %.1f — "
            "if equal, the plan may be substituting the test value for the production operand"
            % (qtv, requested_value))

    @pytest.mark.parametrize("requested_value", [3.0, 5.0, 8.0])
    def test_qualification_test_value_does_not_change_with_requested(self, requested_value):
        """qualification_test_value is constant contract metadata — it must be the
        same regardless of requested value (it's the evidence binding value, not
        the user's value)."""
        brain = _brain()
        results = [
            brain.execute(ProducerRequest(
                user_intent="set Env2.Decay to %.1f seconds" % v,
                semantic_target="Env2.Decay"))
            for v in [3.0, 5.0, 8.0]
        ]
        plans = [getattr(r, "_serum_preset_plan", None) for r in results]
        qtvs = [p.get("qualification_test_value") for p in plans if p]
        # All three must produce the same qualification_test_value (it's contract metadata)
        assert len(set(qtvs)) == 1, (
            "qualification_test_value must be constant contract metadata, "
            "not vary with requested value. Got: %r" % qtvs)

    def test_finalize_signature_has_no_value_param(self):
        """finalize_serum_preset_execution must not accept a value or operand parameter —
        the production operand is in the preset file, not a runtime argument."""
        sig = inspect.signature(ProducerBrain.finalize_serum_preset_execution)
        param_names = set(sig.parameters.keys())
        forbidden = {"value", "operand", "mutation_value", "qualification_test_value",
                     "production_operand", "requested_value"}
        overlap = param_names & forbidden
        assert not overlap, (
            "finalize_serum_preset_execution must not accept value/operand params "
            "(production value is in the preset, not a runtime arg). Found: %r" % overlap)

    def test_finalize_required_params(self):
        """finalize_serum_preset_execution must require preset_sha256 and readback_verified."""
        sig = inspect.signature(ProducerBrain.finalize_serum_preset_execution)
        assert "preset_sha256" in sig.parameters, "preset_sha256 must be required"
        assert "readback_verified" in sig.parameters, "readback_verified must be required"
        assert "ui_readback" in sig.parameters, "ui_readback must be required"


# ---------------------------------------------------------------------------
# Gate B certificate machine-check (cloud-side, no native Serum required)
# ---------------------------------------------------------------------------

class TestGateBCertificate:
    """Machine-checkable Gate B certificate semantics."""

    def _make_result(self, *, execution_status="ADVISORY_ONLY", decision=None,
                     admitted=None, readback_verified=None, preset_sha256=None,
                     module_sha=None, plan=None, restoration_verified=True):
        """Build a minimal ProducerResult for certificate testing."""
        r = ProducerResult(request=ProducerRequest(user_intent="test"))
        r.execution_status = execution_status
        r.decision = decision
        r.admitted = admitted
        if readback_verified is not None or preset_sha256:
            r.serum_preset_execution = {
                "readback_verified": readback_verified,
                "preset_sha256": preset_sha256 or "abc123",
                "ui_readback": {
                    "route": "DIRECT_UI",
                    "values": {},
                    "restoration_verified": restoration_verified,
                    "loader_evidence": {
                        "serum_module_sha256": module_sha,
                        "run_id": "test-run",
                        "track_nonce": "test-nonce",
                    } if module_sha else None,
                },
            }
        if plan:
            r._serum_preset_plan = plan
        return r

    def test_gate_b_blocked_on_advisory_only(self):
        from serum2.producer.gate_b_certificate import gate_b_status
        r = self._make_result(execution_status="ADVISORY_ONLY")
        assert gate_b_status(r) == "GATE_B_BLOCKED"

    def test_gate_b_blocked_on_not_accepted(self):
        from serum2.producer.gate_b_certificate import gate_b_status
        r = self._make_result(execution_status="EXECUTED", decision="REJECTED",
                              readback_verified=False, preset_sha256="abc")
        assert gate_b_status(r) == "GATE_B_BLOCKED"

    def test_gate_b_blocked_on_refused(self):
        from serum2.producer.gate_b_certificate import gate_b_status
        r = self._make_result(execution_status="REFUSED_NO_CONTRACT")
        assert gate_b_status(r) == "GATE_B_BLOCKED"

    def test_native_state_proof_without_admitted(self):
        """EXECUTED + ACCEPTED + readback_verified but admitted=False -> NATIVE_STATE_PROOF."""
        from serum2.producer.gate_b_certificate import gate_b_status
        r = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                              admitted=False, readback_verified=True, preset_sha256="abc")
        assert gate_b_status(r) == "NATIVE_STATE_PROOF"

    def test_native_state_proof_without_module_sha(self):
        """EXECUTED + ACCEPTED + admitted=True but no loader_evidence -> NATIVE_STATE_PROOF."""
        from serum2.producer.gate_b_certificate import gate_b_status
        r = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                              admitted=True, readback_verified=True, preset_sha256="abc",
                              module_sha=None)
        assert gate_b_status(r) == "NATIVE_STATE_PROOF"

    def test_canonical_gate_b_verified(self):
        """Full chain: EXECUTED + ACCEPTED + admitted + bound module SHA -> CANONICAL_GATE_B_VERIFIED."""
        from serum2.producer.gate_b_certificate import gate_b_status
        r = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                              admitted=True, readback_verified=True, preset_sha256="abc",
                              module_sha=EPOCH_2_0_23.binary_sha256)
        assert gate_b_status(r, epoch=EPOCH_2_0_23) == "CANONICAL_GATE_B_VERIFIED"

    def test_native_state_proof_on_wrong_epoch_sha(self):
        """Correct module SHA but wrong epoch -> NATIVE_STATE_PROOF (epoch mismatch)."""
        from serum2.producer.gate_b_certificate import gate_b_status
        r = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                              admitted=True, readback_verified=True, preset_sha256="abc",
                              module_sha="wrongsha256")
        assert gate_b_status(r, epoch=EPOCH_2_0_23) == "NATIVE_STATE_PROOF"

    def test_certificate_dawdreamer_false(self):
        """Certificate must explicitly record DawDreamer=NOT_USED."""
        from serum2.producer.gate_b_certificate import gate_b_certificate
        r = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                              admitted=True, readback_verified=True, preset_sha256="abc",
                              module_sha=EPOCH_2_0_23.binary_sha256)
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23)
        assert cert["dawdreamer_used"] is False
        assert cert["headless_substitution_used"] is False
        assert cert["native_evidence_source"] == "Windows/Ableton/Serum 2.0.23"

    def test_certificate_separation_qualification_from_operand(self):
        """Certificate records qualification_test_value as metadata — no production_operand field."""
        from serum2.producer.gate_b_certificate import gate_b_certificate
        r = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                              admitted=True, readback_verified=True, preset_sha256="abc",
                              module_sha=EPOCH_2_0_23.binary_sha256,
                              plan={"qualification_test_value": 0.5,
                                    "mutation_target_path": "Env1.plainParams.kParamDecay"})
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23)
        assert cert["qualification_test_value"] == 0.5
        assert "production_operand" not in cert, (
            "Certificate must not include a production_operand field — "
            "the operand is in the preset file, not in the certificate")
        assert cert["target_path"] == "Env1.plainParams.kParamDecay"

    def test_gate_b_verified_helper(self):
        """gate_b_verified() helper returns True only for CANONICAL_GATE_B_VERIFIED."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified
        r = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                              admitted=True, readback_verified=True, preset_sha256="abc",
                              module_sha=EPOCH_2_0_23.binary_sha256)
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23)
        assert gate_b_verified(cert) is True
        # NATIVE_STATE_PROOF is not verified
        r2 = self._make_result(execution_status="EXECUTED", decision="ACCEPTED",
                               admitted=False, readback_verified=True, preset_sha256="abc")
        cert2 = gate_b_certificate(r2)
        assert gate_b_verified(cert2) is False


# ---------------------------------------------------------------------------
# Qualification value read classification
# ---------------------------------------------------------------------------

class TestQualificationValueReadClassification:
    """Verify that no runtime code path reads qualification_test_value as a mutation input."""

    def test_qualification_test_value_not_read_in_finalize(self):
        """finalize_serum_preset_execution must not use qualification_test_value or
        mutation_value_used as a subscript/attribute — checking runtime reads, not
        docstring references."""
        import ast
        import os
        brain_path = os.path.join(os.path.dirname(__file__), "..",
                                  "serum2", "producer", "producer_brain.py")
        source = open(brain_path).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "finalize_serum_preset_execution":
                # Collect all string constants used as subscript keys inside the function
                # (excludes docstring, comments, and string literals in non-subscript context)
                subscript_keys = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Subscript):
                        slice_node = child.slice
                        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                            subscript_keys.add(slice_node.value)
                bad = {"qualification_test_value", "mutation_value_used"}
                overlap = subscript_keys & bad
                assert not overlap, (
                    "finalize_serum_preset_execution reads %r as subscript keys — "
                    "the production operand is in the preset file; no plan field may "
                    "be read here as a mutation input" % overlap)
                return
        pytest.fail("finalize_serum_preset_execution not found in producer_brain.py")

    def test_plan_qualification_test_value_label_consistent_across_phrasings(self):
        """The qualification_test_value is the same regardless of how the user phrases
        the request — it's a contract property, not derived from user intent."""
        brain = _brain()
        phrasings = [
            "set Env2.Decay to 5.0 seconds",
            "shorten Env2.Decay to 5 s",
            "make Env2.Decay 5.0 s",
        ]
        qtvs = []
        for intent in phrasings:
            result = brain.execute(ProducerRequest(
                user_intent=intent, semantic_target="Env2.Decay"))
            plan = getattr(result, "_serum_preset_plan", None)
            assert plan is not None
            qtvs.append(plan.get("qualification_test_value"))
        assert len(set(qtvs)) == 1, (
            "qualification_test_value must be constant contract metadata "
            "across phrasings: %r" % qtvs)


# ---------------------------------------------------------------------------
# Tests A–F: operand invariant in gate_b_certificate()
# ---------------------------------------------------------------------------

class TestOperandInvariant:
    """gate_b_certificate() operand invariant: requested==compiled, native~=compiled."""

    _W1_REQUESTED = 5.0
    _W1_COMPILED = 5.0
    _W1_NATIVE_RESAVE = 5.000000000000001  # float64 round-trip from Serum native Save As

    def _make_canonical_result(self):
        """Full canonical chain result suitable for CANONICAL_GATE_B_VERIFIED."""
        from serum2.producer.producer_brain import ProducerResult, ProducerRequest
        r = ProducerResult(request=ProducerRequest(user_intent="test"))
        r.execution_status = "EXECUTED"
        r.decision = "ACCEPTED"
        r.admitted = True
        r.serum_preset_execution = {
            "readback_verified": True,
            "preset_sha256": "0998b65a229b275cc0c93dec290d96544e4297591bac2124d9bcb8bdf83567a0",
            "ui_readback": {
                "route": "DIRECT_UI",
                "values": {"env2.decay": "5.00 s"},
                "restoration_verified": True,
                "loader_evidence": {
                    "serum_module_sha256": EPOCH_2_0_23.binary_sha256,
                    "run_id": "W1_GATE_B_22433E83",
                    "track_nonce": "W1_GATE_B_22433E83",
                },
            },
        }
        r._serum_preset_plan = {
            "mutation_target_path": "Env1.plainParams.kParamDecay",
            "qualification_test_value": 0.5,
        }
        return r

    def test_a_requested_equals_compiled_passes(self):
        """Test A: requested_operand == compiled_operand → CANONICAL_GATE_B_VERIFIED kept."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified
        r = self._make_canonical_result()
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23,
                                   requested_operand=self._W1_REQUESTED,
                                   compiled_operand=self._W1_COMPILED,
                                   native_resave_operand=self._W1_NATIVE_RESAVE)
        assert cert["gate_b_status"] == "CANONICAL_GATE_B_VERIFIED", cert["gate_b_status"]
        assert cert["operand_invariant_status"] == "OPERAND_INVARIANT_VERIFIED"
        assert gate_b_verified(cert) is True

    def test_b_float_round_trip_passes(self):
        """Test B: native_resave ≈ compiled (float64 round-trip) → invariant OK."""
        from serum2.producer.gate_b_certificate import gate_b_certificate
        r = self._make_canonical_result()
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23,
                                   requested_operand=5.0,
                                   compiled_operand=5.0,
                                   native_resave_operand=5.000000000000001)
        assert cert["operand_invariant_status"] == "OPERAND_INVARIANT_VERIFIED"
        assert cert["gate_b_status"] == "CANONICAL_GATE_B_VERIFIED"

    def test_c_requested_mismatch_fails(self):
        """Test C: requested_operand != compiled_operand → downgrade to NATIVE_STATE_PROOF."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified
        r = self._make_canonical_result()
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23,
                                   requested_operand=3.0,   # wrong — doesn't match compiled
                                   compiled_operand=5.0,
                                   native_resave_operand=5.000000000000001)
        assert cert["gate_b_status"] == "NATIVE_STATE_PROOF", cert["gate_b_status"]
        assert cert["operand_invariant_status"] == "OPERAND_MISMATCH_REQUESTED_VS_COMPILED"
        assert gate_b_verified(cert) is False

    def test_d_native_mismatch_fails(self):
        """Test D: native_resave far from compiled → downgrade to NATIVE_STATE_PROOF."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified
        r = self._make_canonical_result()
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23,
                                   requested_operand=5.0,
                                   compiled_operand=5.0,
                                   native_resave_operand=3.0)  # way off — not a float64 artifact
        assert cert["gate_b_status"] == "NATIVE_STATE_PROOF", cert["gate_b_status"]
        assert cert["operand_invariant_status"] == "OPERAND_MISMATCH_NATIVE_VS_COMPILED"
        assert gate_b_verified(cert) is False

    def test_e_missing_operand_blocks(self):
        """Test E: partial operand evidence (only some provided) blocks CANONICAL."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified
        r = self._make_canonical_result()
        # Provide only two of three — should downgrade
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23,
                                   requested_operand=5.0,
                                   compiled_operand=5.0,
                                   native_resave_operand=None)  # missing
        assert cert["gate_b_status"] == "NATIVE_STATE_PROOF", cert["gate_b_status"]
        assert cert["operand_invariant_status"] == "INCOMPLETE_OPERAND_EVIDENCE"
        assert gate_b_verified(cert) is False

    def test_f_qualification_separation_maintained(self):
        """Test F: qualification_test_value (0.5) must differ from requested_operand (5.0)."""
        from serum2.producer.gate_b_certificate import gate_b_certificate
        r = self._make_canonical_result()
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23,
                                   requested_operand=self._W1_REQUESTED,
                                   compiled_operand=self._W1_COMPILED,
                                   native_resave_operand=self._W1_NATIVE_RESAVE)
        assert cert["qualification_test_value"] == 0.5, (
            "qualification_test_value must be the binding-test metadata value (0.5), "
            "not the production operand")
        assert cert["requested_operand"] == 5.0
        assert cert["qualification_test_value"] != cert["requested_operand"], (
            "qualification_test_value must differ from requested_operand — "
            "they are different things: binding-test metadata vs user production value")

    def test_no_operands_backward_compat(self):
        """gate_b_certificate() without operands → CANONICAL still works (backward compat)."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified
        r = self._make_canonical_result()
        cert = gate_b_certificate(r, epoch=EPOCH_2_0_23)
        assert cert["gate_b_status"] == "CANONICAL_GATE_B_VERIFIED"
        assert cert["operand_invariant_status"] == "OPERAND_EVIDENCE_NOT_PROVIDED"
        assert cert["requested_operand"] is None
        assert cert["compiled_operand"] is None
        assert cert["native_resave_operand"] is None
        assert gate_b_verified(cert) is True  # backward compat — no operands doesn't block
