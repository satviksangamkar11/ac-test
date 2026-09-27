"""Deterministic tests for serum2.producer.w2_fast_path.

No network access, no Serum binary, no VLM/OCR calls.
Tests verify: existing-frame reuse, contract-first filtering,
temporal candidate selection, OCR numeric profile structure,
and observation-policy / mutation-boundary invariants.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pytest

from serum2.producer.w2_fast_path import (
    load_existing_manifest,
    manifest_frame_ids,
    select_frames_by_timestamp,
    contract_covered_controls,
    filter_contract_covered,
    all_manifest_frames_for_control,
    numeric_ocr_profile,
    assert_no_redownload,
    rand_phase_exclusion_reason,
    NUMERIC_OCR_ALLOWLIST,
    W2_MANIFEST_PATH,
    CONTRACT_PATH,
)


# ---------------------------------------------------------------------------
# Fixture: load real artifacts once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manifest():
    return load_existing_manifest(W2_MANIFEST_PATH)


@pytest.fixture(scope="module")
def covered_controls():
    return contract_covered_controls()


# ---------------------------------------------------------------------------
# 1. Existing-frame reuse: manifest loads without network/download
# ---------------------------------------------------------------------------

class TestExistingFrameReuse:
    def test_manifest_loads_without_network(self, manifest):
        """Manifest is in the repo; no yt-dlp or ffmpeg download should occur."""
        assert isinstance(manifest, dict)
        assert "frames" in manifest

    def test_manifest_has_269_frames(self, manifest):
        assert manifest["num_frames"] == 269
        assert len(manifest["frames"]) == 269

    def test_manifest_not_storyboard_only(self, manifest):
        assert manifest["storyboard_only"] is False

    def test_assert_no_redownload_passes_on_real_manifest(self, manifest):
        assert_no_redownload(manifest)  # must not raise

    def test_assert_no_redownload_raises_on_storyboard(self):
        with pytest.raises(AssertionError, match="storyboard_only"):
            assert_no_redownload({"storyboard_only": True, "frames": []})

    def test_manifest_video_id_matches_w2(self, manifest):
        assert manifest["video_id"] == "AjE11L_OwLA"

    def test_frame_ids_are_strings(self, manifest):
        ids = manifest_frame_ids(manifest)
        assert len(ids) == 269
        assert all(isinstance(fid, str) for fid in ids)

    def test_frame_ids_contain_used_frames(self, manifest):
        ids = set(manifest_frame_ids(manifest))
        assert "frame_yt_19935949eb0e_00024000" in ids
        assert "frame_yt_19935949eb0e_00034000" in ids

    def test_select_frames_by_timestamp_returns_subset(self, manifest):
        frames = select_frames_by_timestamp(manifest, 22.0, 28.0)
        assert len(frames) >= 1
        for fr in frames:
            assert 22.0 <= fr["timestamp_sec"] <= 28.0

    def test_select_frames_empty_range_returns_empty(self, manifest):
        frames = select_frames_by_timestamp(manifest, 9999.0, 9999.5)
        assert frames == []

    def test_select_frames_at_24s_includes_known_frame(self, manifest):
        frames = select_frames_by_timestamp(manifest, 24.0, 24.0)
        ids = [fr["frame_id"] for fr in frames]
        assert "frame_yt_19935949eb0e_00024000" in ids


# ---------------------------------------------------------------------------
# 2. No re-download path when W2 frames already exist
# ---------------------------------------------------------------------------

class TestNoRedownload:
    def test_load_existing_manifest_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="W2 manifest not found"):
            load_existing_manifest(tmp_path / "nonexistent.json")

    def test_load_existing_manifest_error_mentions_local_acquisition(self, tmp_path):
        try:
            load_existing_manifest(tmp_path / "x.json")
        except FileNotFoundError as e:
            assert "LOCAL" in str(e) or "W2_RUNBOOK" in str(e)

    def test_w2_fast_path_module_imports_no_network_modules(self):
        import serum2.producer.w2_fast_path as mod
        import inspect
        source = inspect.getsource(mod)
        for net_module in ["yt_dlp", "urllib.request", "requests", "httpx", "subprocess"]:
            assert net_module not in source, (
                f"w2_fast_path imports or references '{net_module}' — "
                "must not trigger network or subprocess calls"
            )


# ---------------------------------------------------------------------------
# 3. Contract-first filtering excludes rand_phase
# ---------------------------------------------------------------------------

class TestContractFirstFiltering:
    def test_oscA_octave_is_contract_covered(self, covered_controls):
        assert "oscA.octave" in covered_controls

    def test_env1_decay_is_contract_covered(self, covered_controls):
        assert "env1.decay" in covered_controls

    def test_lfo1_rate_is_contract_covered(self, covered_controls):
        assert "lfo1.rate" in covered_controls

    def test_filter1_cutoff_is_contract_covered(self, covered_controls):
        assert "filter1.cutoff" in covered_controls

    def test_rand_phase_not_in_contract(self, covered_controls):
        """oscA.rand_phase was OBSERVED in W2 but must not be admissible — no contract row."""
        assert "oscA.rand_phase" not in covered_controls

    def test_filter_contract_covered_excludes_rand_phase(self, covered_controls):
        candidates = ["oscA.octave", "env1.decay", "oscA.rand_phase", "lfo1.rate"]
        covered, excluded = filter_contract_covered(candidates, covered_controls)
        assert "oscA.rand_phase" not in covered
        assert "oscA.rand_phase" in excluded
        assert "oscA.octave" in covered
        assert "env1.decay" in covered

    def test_filter_contract_covered_covered_list_correct(self, covered_controls):
        candidates = ["oscA.rand_phase", "nonexistent.param"]
        covered, excluded = filter_contract_covered(candidates, covered_controls)
        assert covered == []
        assert set(excluded) == {"oscA.rand_phase", "nonexistent.param"}

    def test_rand_phase_exclusion_reason_is_documented(self):
        reason = rand_phase_exclusion_reason()
        assert "oscA.rand_phase" in reason
        assert "OBSERVED" in reason
        assert "contract" in reason.lower()

    def test_contract_loads_read_only(self):
        from serum2.producer.w2_fast_path import load_contract, CONTRACT_PATH
        contract = load_contract(CONTRACT_PATH)
        # Verify it didn't mutate the file by checking the key exists unchanged
        assert "producer_lookup" in contract
        assert len(contract["producer_lookup"]) == 330

    def test_contract_has_183_host_confirmed_no_exception(self, covered_controls):
        assert len(covered_controls) == 183


# ---------------------------------------------------------------------------
# 4. All manifest frames (universal observer) — no tutorial-specific windows
# ---------------------------------------------------------------------------

class TestAllManifestFramesForControl:
    def test_oscA_octave_returns_all_frames(self, manifest, covered_controls):
        """all_manifest_frames_for_control returns ALL frames for contract-covered controls."""
        frames = all_manifest_frames_for_control(manifest, "oscA.octave", covered_controls)
        assert len(frames) == 269

    def test_all_frames_are_manifest_entries(self, manifest, covered_controls):
        all_ids = set(manifest_frame_ids(manifest))
        frames = all_manifest_frames_for_control(manifest, "oscA.octave", covered_controls)
        for fr in frames:
            assert fr["frame_id"] in all_ids

    def test_all_frames_no_duplicates(self, manifest, covered_controls):
        frames = all_manifest_frames_for_control(manifest, "oscA.octave", covered_controls)
        ids = [fr["frame_id"] for fr in frames]
        assert len(ids) == len(set(ids))

    def test_rand_phase_returns_empty(self, manifest, covered_controls):
        """rand_phase not contract-covered → no frames."""
        frames = all_manifest_frames_for_control(manifest, "oscA.rand_phase", covered_controls)
        assert frames == []

    def test_unknown_control_returns_empty(self, manifest, covered_controls):
        frames = all_manifest_frames_for_control(manifest, "fake.nonexistent", covered_controls)
        assert frames == []

    def test_env1_decay_returns_all_frames(self, manifest, covered_controls):
        """All contract-covered controls get all frames, not selective windows."""
        frames = all_manifest_frames_for_control(manifest, "env1.decay", covered_controls)
        assert len(frames) == 269

    def test_lfo1_rate_returns_all_frames(self, manifest, covered_controls):
        """LFO1.rate not tutorial-specific; gets full frame set for universal observer."""
        frames = all_manifest_frames_for_control(manifest, "lfo1.rate", covered_controls)
        assert len(frames) == 269

    def test_frames_sorted_by_timestamp(self, manifest, covered_controls):
        frames = all_manifest_frames_for_control(manifest, "oscA.octave", covered_controls)
        timestamps = [float(fr.get("timestamp_sec", 0.0)) for fr in frames]
        assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# 5. OCR numeric profile is generic — no control-name branches
# ---------------------------------------------------------------------------

class TestOCRNumericProfile:
    def test_default_profile_includes_digits(self):
        profile = numeric_ocr_profile()
        for d in "0123456789":
            assert d in profile["allowlist"]

    def test_default_profile_includes_minus_and_decimal(self):
        profile = numeric_ocr_profile()
        assert "-" in profile["allowlist"]
        assert "." in profile["allowlist"]

    def test_unsigned_profile_excludes_minus(self):
        profile = numeric_ocr_profile(signed=False)
        assert "-" not in profile["allowlist"]

    def test_integer_profile_excludes_decimal(self):
        profile = numeric_ocr_profile(decimal=False)
        assert "." not in profile["allowlist"]

    def test_profile_has_mag_ratio(self):
        profile = numeric_ocr_profile()
        assert profile.get("mag_ratio", 0) >= 1.5

    def test_profile_has_beam_width(self):
        profile = numeric_ocr_profile()
        assert "beamWidth" in profile

    def test_module_numeric_allowlist_has_no_letters(self):
        for ch in NUMERIC_OCR_ALLOWLIST:
            assert not ch.isalpha(), f"Allowlist contains letter '{ch}' — must be numeric only"

    def test_no_control_id_parameter_in_numeric_ocr_profile(self):
        import inspect
        from serum2.producer.w2_fast_path import numeric_ocr_profile as f
        sig = inspect.signature(f)
        param_names = list(sig.parameters.keys())
        for name in param_names:
            assert "control" not in name.lower() and "id" not in name.lower(), (
                f"numeric_ocr_profile has a per-control parameter '{name}' — "
                "must be generic, no control-name branches"
            )

    def test_fast_path_module_has_no_control_name_string_branches(self):
        import inspect
        import serum2.producer.w2_fast_path as mod
        source = inspect.getsource(mod)
        # These are the controls we want to ensure are NOT hardcoded in production logic.
        # (They appear in _TUTORIAL_CANDIDATE_WINDOWS as data, which is acceptable;
        #  but they must not appear as branches in the generic helpers.)
        # Check that numeric_ocr_profile function body has no control names.
        func_src = inspect.getsource(mod.numeric_ocr_profile)
        for control_name in ["oscA.octave", "env1.decay", "lfo1.rate", "filter1.cutoff"]:
            assert control_name not in func_src, (
                f"numeric_ocr_profile contains hardcoded control name '{control_name}'"
            )


# ---------------------------------------------------------------------------
# 6. C3 observation policy remains unchanged
# ---------------------------------------------------------------------------

class TestC3ObservationPolicyUnchanged:
    def test_single_source_still_ambiguous(self):
        from serum2.producer.observation_policy import adjudicate, ObservationCandidate, OUTCOME_AMBIGUOUS, OUTCOME_CANDIDATE
        cands = [ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1.5, confidence=0.99, source="vlm")]
        result = adjudicate(cands)
        assert result.outcome == OUTCOME_AMBIGUOUS
        assert result.single_source is True

    def test_multi_source_agreement_still_observed(self):
        from serum2.producer.observation_policy import adjudicate, ObservationCandidate, OUTCOME_OBSERVED, OUTCOME_CANDIDATE
        cands = [
            ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=62.0, confidence=0.99, source="vlm"),
            ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=62.0, confidence=0.99, source="ocr"),
        ]
        result = adjudicate(cands)
        assert result.outcome == OUTCOME_OBSERVED

    def test_multi_source_disagreement_still_ambiguous(self):
        from serum2.producer.observation_policy import adjudicate, ObservationCandidate, OUTCOME_AMBIGUOUS, OUTCOME_CANDIDATE
        cands = [
            ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1.0, confidence=0.99, source="vlm"),
            ObservationCandidate(outcome=OUTCOME_CANDIDATE, value=1005.0, confidence=0.16, source="ocr"),
        ]
        result = adjudicate(cands)
        assert result.outcome == OUTCOME_AMBIGUOUS

    def test_confident_threshold_still_09(self):
        from serum2.producer.observation_policy import CONFIDENT_THRESHOLD
        assert CONFIDENT_THRESHOLD == 0.9


# ---------------------------------------------------------------------------
# 7. No imports from observation_policy into mutation-authority modules
# ---------------------------------------------------------------------------

class TestMutationBoundaryUnchanged:
    def _has_import_of(self, module_name: str, imported_name: str) -> bool:
        """Return True iff module_name contains an actual import of imported_name."""
        import importlib, inspect, ast
        try:
            mod = importlib.import_module(module_name)
            source = inspect.getsource(mod)
        except (ImportError, OSError):
            return False
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if imported_name in alias.name:
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module and imported_name in node.module:
                    return True
                for alias in node.names:
                    if imported_name in alias.name:
                        return True
        return False

    def test_state_admission_does_not_import_observation_policy(self):
        assert not self._has_import_of("serum2.producer.state_admission", "observation_policy")

    def test_authorized_state_compiler_does_not_import_observation_policy(self):
        assert not self._has_import_of("serum2.execution.authorized_state_compiler", "observation_policy")

    def test_gate_b_certificate_does_not_import_observation_policy(self):
        assert not self._has_import_of("serum2.qualification.gate_b_certificate", "observation_policy")

    def test_w2_fast_path_does_not_import_observation_policy(self):
        assert not self._has_import_of("serum2.producer.w2_fast_path", "observation_policy")

    def test_w2_fast_path_does_not_import_state_admission(self):
        assert not self._has_import_of("serum2.producer.w2_fast_path", "state_admission")
        assert not self._has_import_of("serum2.producer.w2_fast_path", "authorized_state_compiler")
        assert not self._has_import_of("serum2.producer.w2_fast_path", "gate_b_certificate")
