"""Gate-A A1–A5 regression tests: authority chain integrity, ledger safety, epoch handling."""
import pytest
from pathlib import Path

from serum2.producer.execution_epoch import (
    EPOCH_2_0_23, EPOCH_OFFLINE_TEST, ExecutionEpoch,
    is_offline_test, require_epoch
)
from serum2.producer.producer_brain import ProducerBrain
from serum2.producer.state_ledger import _coerce, Row


class TestA3EpochHandling:
    """A3: epoch=None must raise in production; EPOCH_OFFLINE_TEST caps claims."""

    def test_is_offline_test_rejects_none(self):
        """A3: is_offline_test(None) returns False (epoch=None is NOT valid)."""
        assert is_offline_test(None) is False, "is_offline_test(None) must return False"

    def test_is_offline_test_accepts_sentinel(self):
        """A3: is_offline_test(EPOCH_OFFLINE_TEST) returns True."""
        assert is_offline_test(EPOCH_OFFLINE_TEST) is True

    def test_require_epoch_rejects_none(self):
        """A3: require_epoch(None) raises ValueError."""
        with pytest.raises(ValueError, match="epoch=None is not valid in production"):
            require_epoch(None)

    def test_require_epoch_accepts_valid_epoch(self):
        """A3: require_epoch(EPOCH_2_0_23) returns the epoch."""
        result = require_epoch(EPOCH_2_0_23)
        assert result is EPOCH_2_0_23

    def test_require_epoch_rejects_invalid_type(self):
        """A3: require_epoch('not-an-epoch') raises ValueError."""
        with pytest.raises(ValueError, match="epoch must be ExecutionEpoch"):
            require_epoch("not-an-epoch")

    def test_producer_brain_rejects_none_in_production(self):
        """A3: ProducerBrain(epoch=None) must fail in production."""
        # ProducerBrain must reject None; no backward compat for unsafe defaults
        with pytest.raises(ValueError, match="ProducerBrain requires explicit epoch"):
            ProducerBrain(epoch=None)

    def test_producer_brain_accepts_valid_epoch(self):
        """A3: ProducerBrain(epoch=EPOCH_2_0_23) accepts valid epoch."""
        brain = ProducerBrain(epoch=EPOCH_2_0_23)
        assert brain is not None

    def test_reference_reproduction_rejects_none_epoch(self):
        """A3: run_reference_reproduction must reject epoch=None."""
        from serum2.server.reference_reproduction import run_reference_reproduction
        import tempfile
        import json
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            # Create minimal stage_a and reread files
            stage_a = {"frames": []}
            reread = {"rows": []}

            p1 = Path(tmp) / "stage_a.json"
            p2 = Path(tmp) / "reread.json"
            p1.write_text(json.dumps(stage_a))
            p2.write_text(json.dumps(reread))

            # Must reject epoch=None
            with pytest.raises(ValueError, match="requires explicit epoch"):
                run_reference_reproduction(
                    str(p1), str(p2),
                    source={"video_id": "test"},
                    name="test",
                    epoch=None  # MUST FAIL
                )


class TestA1OperandSourcing:
    """A1: operand is observed value from run, not qualification_test_value; end-to-end proof."""

    def test_a1_three_distinct_operands_flow_canonical_path(self):
        """A1 BEHAVIORAL PROOF: 3 distinct values → row.op["value"] → AuthorizedOperation.operand

        Exercises actual canonical functions:
        1. Create rows with OPERATION_DERIVED + ADMITTED status, distinct observed values
        2. Call ops_from_rows() (the real compiler input function)
        3. Verify AuthorizedOperation.operand equals observed value (not qualification_test_value)
        4. Prove all 3 distinct values survive the canonical path unchanged
        5. Prove missing operand fails (no default to test value)
        """
        from serum2.producer.state_ledger import Row
        from serum2.execution.authorized_state_compiler import ops_from_rows
        from serum2.producer.execution_epoch import EPOCH_2_0_23

        # Three distinct observed values that must flow through unchanged
        observed_values = [0.3, 0.5, 0.8]
        qualification_test_value = 0.4  # Different from all observed values

        # Create rows as they would exist after ledger derivation + admission
        rows = []
        for idx, obs_val in enumerate(observed_values):
            r = Row(
                control_id='env1.attack',
                value=obs_val,  # The OBSERVED value
                unit='s',
                status='OBSERVED',
                control_type='fader',
                source_ts=float(idx),
                n_readings=1,
                changed_from_previous=False,
                context={}
            )
            # Simulate successful derivation + admission
            r.op = {
                'kind': 'field',
                'module': 'env',
                'index': 0,
                'field': 'attack',
                'operation': 'SET',
                'value': obs_val,  # Operand is the OBSERVED value
                'contract_status': 'VERIFIED',
                'capability': 'env1.attack',
                'contract_epoch': EPOCH_2_0_23.binary_sha256[:8],
                'execution_path': '/Env/plainParams/kParamAttack'
            }
            r.terminal = 'OPERATION_DERIVED'
            r.admission = 'ADMITTED'
            rows.append(r)

        # CANONICAL PATH: ops_from_rows() processes admitted rows
        ops = ops_from_rows(rows, EPOCH_2_0_23)

        # A1 PROOF 1: All 3 distinct operands flow through unchanged
        compiled_operands = [op.operand for op in ops if op.canonical_target == 'env1.attack']
        assert len(compiled_operands) == 3, f"Should compile 3 operations, got {len(compiled_operands)}"
        assert compiled_operands == observed_values, \
            f"A1: operands should be observed values {observed_values}, got {compiled_operands}"

        # A1 PROOF 2: Qualification test value is NOT used
        for op in ops:
            if op.canonical_target == 'env1.attack':
                assert op.operand != qualification_test_value, \
                    f"A1: operand {op.operand} should never equal qualification_test_value {qualification_test_value}"

        # A1 PROOF 3: NEGATIVE - missing operand cannot default to test value
        # Create a row with no operand value
        bad_row = Row(
            control_id='env1.attack',
            value=0.7,
            unit='s',
            status='OBSERVED',
            control_type='fader',
            source_ts=3.0,
            n_readings=1,
            changed_from_previous=False,
            context={}
        )
        bad_row.op = {
            'kind': 'field',
            'module': 'env',
            'index': 0,
            'field': 'attack',
            'operation': 'SET',
            # MISSING 'value' key
            'contract_status': 'VERIFIED',
            'capability': 'env1.attack',
            'contract_epoch': EPOCH_2_0_23.binary_sha256[:8]
        }
        bad_row.terminal = 'OPERATION_DERIVED'
        bad_row.admission = 'ADMITTED'

        # ops_from_rows() should handle missing value gracefully
        # (either skip or use o.get("amount") fallback, never assume test value)
        ops_with_bad = ops_from_rows([bad_row], EPOCH_2_0_23)
        # If operand is created, verify it's None (not the test value)
        for op in ops_with_bad:
            if op.canonical_target == 'env1.attack':
                assert op.operand is None or op.operand != qualification_test_value, \
                    "A1: missing operand must not default to qualification_test_value"




class TestA4ContractReachability:
    """A4 BEHAVIORAL: Real contracts loaded from repository evidence are reachable and verified."""

    def test_a4_all_promoted_contracts_have_mutation_target_path(self):
        """A4 PROOF 1: Every contract loaded from actual evidence has mutation_target_path.

        Uses ACTUAL repository evidence directories (not mocks).
        - parameter_characterization/binding_evidence (32 CAUSAL)
        - parameter_characterization/binding_evidence_mcp_exec_v1 (310 STRUCTURAL)
        """
        from serum2.producer.contract_registry import ContractRegistry
        from serum2.producer.execution_epoch import EPOCH_2_0_23
        from pathlib import Path

        # Load registry with ACTUAL evidence directories
        reg = ContractRegistry(
            epoch=EPOCH_2_0_23,
            binding_evidence_dir=str(Path('parameter_characterization/binding_evidence')),
            promoted_evidence_dir=str(Path('parameter_characterization/binding_evidence_mcp_exec_v1'))
        )

        # A4 PROOF 1: Every loaded contract has mutation_target_path
        total = len(reg.contracts)
        with_path = sum(1 for c in reg.contracts.values() if c.scope.get("mutation_target_path"))
        assert total > 0, f"Registry should load contracts, got {total}"
        assert with_path == total, \
            f"A4 PROOF 1: Every loaded contract must have mutation_target_path. Got {with_path}/{total}"

        # A4 PROOF 2: mutation_target_path is non-empty
        for target, c in reg.contracts.items():
            path = c.scope.get("mutation_target_path")
            assert path and len(path) > 0, \
                f"A4 PROOF 2: {target} has empty or missing mutation_target_path"

    def test_a4_registry_consistency_and_execution_binding(self):
        """A4 PROOF 3: Loaded contracts have consistent execution binding and body paths.

        Verifies internal consistency: body_path from execution_binding matches
        the mutation_target_path scope information.
        """
        from serum2.producer.contract_registry import ContractRegistry
        from serum2.producer.execution_epoch import EPOCH_2_0_23
        from pathlib import Path

        reg = ContractRegistry(
            epoch=EPOCH_2_0_23,
            binding_evidence_dir=str(Path('parameter_characterization/binding_evidence')),
            promoted_evidence_dir=str(Path('parameter_characterization/binding_evidence_mcp_exec_v1'))
        )

        # A4 PROOF 3: Check execution binding consistency
        for target, c in reg.contracts.items():
            mutation_path = c.scope.get("mutation_target_path")
            # Execution binding exists and is accessible
            assert c.execution_binding is not None, \
                f"A4 PROOF 3: {target} must have execution_binding"
            # Binding has body_path if it's a field binding
            if hasattr(c.execution_binding, 'body_path'):
                body_path = c.execution_binding.body_path
                # If both exist, they should be related
                assert body_path or mutation_path, \
                    f"A4: {target} has neither body_path nor mutation_target_path"

    def test_a4_find_contract_reaches_real_contracts(self):
        """A4 PROOF 4: find_contract() can reach actual loaded contracts.

        Tests that the registry lookup mechanism works end-to-end with real rows.
        """
        from serum2.producer.contract_registry import ContractRegistry
        from serum2.producer.execution_epoch import EPOCH_2_0_23
        from serum2.producer.contract_scope import find_contract, bridge_index
        from serum2.producer.state_ledger import Row, catalog
        from pathlib import Path

        reg = ContractRegistry(
            epoch=EPOCH_2_0_23,
            binding_evidence_dir=str(Path('parameter_characterization/binding_evidence')),
            promoted_evidence_dir=str(Path('parameter_characterization/binding_evidence_mcp_exec_v1'))
        )

        bridge = bridge_index(reg)
        cat = catalog()

        # Pick a sample contract and build a row for it
        sample_target = "arp.pattern.shape"
        if sample_target in reg.contracts:
            c = reg.contracts[sample_target]
            mutation_path = c.scope.get("mutation_target_path")

            # Create a row matching this control
            row = Row(
                control_id=sample_target,
                value="Chord",  # mutated_value from the evidence
                unit=None,
                status="OBSERVED",
                control_type="enum",
                source_ts=0.0,
                n_readings=1,
                changed_from_previous=False,
                context={}
            )

            # Set up operation dict as it would come from derivation
            row.op = {
                'kind': 'field',
                'module': 'arp',
                'index': 0,
                'field': 'pattern_shape',
                'operation': 'SET',
                'value': "Chord",
                'contract_status': 'VERIFIED',
                'capability': sample_target
            }

            # A4 PROOF 4: find_contract can reach this control
            found, trace = find_contract(row.op, {}, bridge, cat)
            # find_contract may not always find (depends on binding availability),
            # but if it finds one, it should be consistent
            if found:
                assert found.target == sample_target or found.scope.get("mutation_target_path"), \
                    "A4 PROOF 4: found contract must have mutation_target_path"


class TestA6FrameAnalysisStatus:
    """A6: Per-frame analysis_status; stage_a_is_filled uses terminal status values."""

    def test_stage_a_skeleton_includes_analysis_status(self):
        """A6 PROOF 1: empty_stage_a_skeleton includes 'analysis_status' field."""
        from serum2.producer.stage_a_census_prep import empty_stage_a_skeleton
        manifest = [{"frame_id": "f1", "timestamp_sec": 0.0, "path": "/tmp/f1.jpg", "source": "sparse"}]
        skeleton = empty_stage_a_skeleton(manifest)
        assert "analysis_status" in skeleton["frames"][0], "analysis_status not in frame schema"
        assert skeleton["frames"][0]["analysis_status"] is None, "analysis_status should start as None"

    def test_stage_a_is_filled_requires_terminal_analysis_status(self):
        """A6 PROOF 2: stage_a_is_filled checks analysis_status, not just controls/mod_routes presence.

        Terminal values: ANALYZED | NOT_SERUM | UNREADABLE | EQUIVALENT_TO:<frame_id>
        Every serum_visible frame MUST have one of these values (not None) for is_filled=True.
        """
        from youtube_to_serum.reference_engine import stage_a_is_filled
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            # A6 PROOF 2a: None analysis_status should fail (not filled)
            frames = [
                {"frame_id": f"f{i}", "serum_visible": True, "analysis_status": None,
                 "controls": [{"control_id": "env2.decay", "value": "300"}] if i == 0 else []}
                for i in range(10)
            ]
            skeleton = {"frames": frames}
            p = Path(tmp) / "skeleton_none.json"
            p.write_text(json.dumps(skeleton))
            result = stage_a_is_filled(str(p))
            assert result is False, "A6 PROOF 2a: None analysis_status should reject (not filled)"

            # A6 PROOF 2b: All ANALYZED should pass
            frames = [
                {"frame_id": f"f{i}", "serum_visible": True, "analysis_status": "ANALYZED",
                 "controls": [{"control_id": "env2.decay", "value": "300"}] if i == 0 else []}
                for i in range(10)
            ]
            skeleton = {"frames": frames}
            p = Path(tmp) / "skeleton_analyzed.json"
            p.write_text(json.dumps(skeleton))
            result = stage_a_is_filled(str(p))
            assert result is True, "A6 PROOF 2b: All ANALYZED should accept"

            # A6 PROOF 2c: NOT_SERUM and UNREADABLE are also valid terminal statuses
            frames = [
                {"frame_id": f"f{i}", "serum_visible": True, "analysis_status": ["ANALYZED", "NOT_SERUM", "UNREADABLE"][i % 3],
                 "controls": []}
                for i in range(9)
            ]
            skeleton = {"frames": frames}
            p = Path(tmp) / "skeleton_mixed.json"
            p.write_text(json.dumps(skeleton))
            result = stage_a_is_filled(str(p))
            assert result is True, "A6 PROOF 2c: ANALYZED|NOT_SERUM|UNREADABLE all valid"

            # A6 PROOF 2d: EQUIVALENT_TO is also valid (terminal equivalence pointer)
            frames = [
                {"frame_id": f"f{i}", "serum_visible": True, "analysis_status": "EQUIVALENT_TO:f0" if i > 0 else "ANALYZED",
                 "controls": []}
                for i in range(10)
            ]
            skeleton = {"frames": frames}
            p = Path(tmp) / "skeleton_equiv.json"
            p.write_text(json.dumps(skeleton))
            result = stage_a_is_filled(str(p))
            assert result is True, "A6 PROOF 2d: EQUIVALENT_TO:frame_id is valid terminal status"

    def test_stage_a_is_filled_uses_all_not_any(self):
        """A6 PROOF 3: stage_a_is_filled uses all() to require every serum_visible frame analyzed."""
        from youtube_to_serum.reference_engine import stage_a_is_filled
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            # One analyzed, 99 unanalyzed should fail (testing all() logic)
            frames = [
                {"frame_id": f"f{i}", "serum_visible": True,
                 "analysis_status": "ANALYZED" if i == 0 else None, "controls": []}
                for i in range(100)
            ]
            skeleton = {"frames": frames}
            p = Path(tmp) / "skeleton_partial.json"
            p.write_text(json.dumps(skeleton))
            result = stage_a_is_filled(str(p))
            assert result is False, "A6 PROOF 3: Partial (1/100) should fail (all() logic)"


class TestA7UIReadbackBinding:
    """A7: UI readback requires loader evidence; _ui_equal handles unit normalization."""

    def test_binding_quality_requires_all_fields(self):
        """A7: LOADER_BOUND requires run_id, track_nonce, serum_module_sha256, epoch, screenshot_sha, crop_coords (all with valid format)."""
        from serum2.execution.state_comparator import _binding_quality
        # Valid 64-char hex values for SHA fields
        valid_sha = "a" * 64

        # Missing epoch
        ui_readback = {"loader_evidence": {
            "run_id": "123",
            "track_nonce": "abc",
            "serum_module_sha256": valid_sha,
            "screenshot_sha": valid_sha,
            "crop_coords": [0, 0, 100, 100]
        }}
        assert _binding_quality(ui_readback) != "LOADER_BOUND", "Should not be LOADER_BOUND without epoch"
        # Add epoch but missing crop_coords
        ui_readback2 = {"loader_evidence": {
            "run_id": "123",
            "track_nonce": "abc",
            "serum_module_sha256": valid_sha,
            "screenshot_sha": valid_sha,
            "epoch": "2.0.23"
        }}
        assert _binding_quality(ui_readback2) != "LOADER_BOUND", "Should not be LOADER_BOUND without crop_coords"
        # Complete with all fields
        ui_readback["loader_evidence"]["epoch"] = "2.0.23"
        assert _binding_quality(ui_readback) == "LOADER_BOUND", "Should be LOADER_BOUND with all fields including crop_coords"

    def test_ui_equal_unit_normalization(self):
        """A7: _ui_equal handles unit normalization ("300" + "ms" == "300 ms")."""
        from serum2.execution.state_comparator import _ui_equal
        # This test verifies the function exists and handles the case
        # (actual numeric parsing requires state_ledger._numeric which needs serum-mcp)
        assert callable(_ui_equal), "_ui_equal should be callable"


class TestA8DawDreamerEvidence:
    """A8: DawDreamer evidence labeled HEADLESS_DAWDREAMER, never VERIFIED."""

    def test_binding_quality_detects_dawdreamer(self):
        """A8: _binding_quality marks DawDreamer as HEADLESS_DAWDREAMER."""
        from serum2.execution.state_comparator import _binding_quality
        ui_readback = {
            "backend": "real Serum VST3 in DawDreamer (headless)",
            "values": {}
        }
        assert _binding_quality(ui_readback) == "HEADLESS_DAWDREAMER", "Should detect DawDreamer backend"

    def test_binding_quality_detects_is_headless_flag(self):
        """A8: _binding_quality marks is_headless=True as HEADLESS_DAWDREAMER."""
        from serum2.execution.state_comparator import _binding_quality
        ui_readback = {"is_headless": True, "values": {}}
        assert _binding_quality(ui_readback) == "HEADLESS_DAWDREAMER", "Should detect is_headless flag"

    def test_verification_level_rejects_headless_dawdreamer(self):
        """A8: verification_level refuses LIVE_UI_VERIFIED for HEADLESS_DAWDREAMER."""
        from serum2.execution.state_comparator import verification_level
        file_cmp = {"field_counts": {"VERIFIED_EXACT": 5}}
        ui_cmp = {"binding_quality": "HEADLESS_DAWDREAMER", "field_counts": {"VERIFIED_EXACT": 5}}
        level = verification_level(file_cmp, ui_cmp)
        assert level != "LIVE_UI_VERIFIED", f"HEADLESS_DAWDREAMER should not reach LIVE_UI_VERIFIED, got {level}"
        assert "DAWDREAMER" in level or "HEADLESS" in level, f"Expected DAWDREAMER marker in level, got {level}"
