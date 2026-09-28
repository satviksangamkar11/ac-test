"""Focused regression tests for the 3 Stage-7 ROI coverage failure classes.

Class 1: element_kind=None controls (oscA.crs, oscB/C.wavetable) now get strategy via control_type fallback.
Class 2: _run_vlm_on_crop / _transcribe_roi no longer pass output_scores=True (was corrupting 4-bit generation).
Class 3: _locate_control_bbox uses Atlas display_name in prompt; OCT/SEM/FIN/CRS siblings have crop entries.

These tests are import-only (no GPU required) — they verify the code paths without running actual inference.
"""
import sys
import types
import importlib
from unittest.mock import MagicMock, patch, call
from pathlib import Path

# ---------------------------------------------------------------------------
# Class 1: resolve_observation_type control_type fallback
# ---------------------------------------------------------------------------

def test_resolve_obs_type_element_kind_none_continuous():
    """Control with element_kind=None + control_type=continuous -> ("NUMERIC", "NUMERIC")."""
    # Root must be on sys.path for serum2.* imports inside expected_inventory.
    root = str(Path(__file__).parent.parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    sys.path.insert(0, str(Path(__file__).parent))
    from expected_inventory import resolve_observation_type
    # oscA.crs has element_kind=None, control_type=continuous in the live Atlas.
    result = resolve_observation_type("oscA.crs")
    assert result == ("NUMERIC", "NUMERIC"), "oscA.crs: expected NUMERIC strategy, got %r" % (result,)


def test_resolve_obs_type_element_kind_none_enum():
    """Control with element_kind=None + control_type=enum -> ("ENUM", "ENUM")."""
    from expected_inventory import resolve_observation_type
    # oscB.wavetable has element_kind=None, control_type=enum in the live Atlas.
    result = resolve_observation_type("oscB.wavetable")
    assert result == ("ENUM", "ENUM"), "oscB.wavetable: expected ENUM strategy, got %r" % (result,)


def test_resolve_obs_type_element_kind_none_enum_c():
    """oscC.wavetable: same as oscB case."""
    from expected_inventory import resolve_observation_type
    result = resolve_observation_type("oscC.wavetable")
    assert result == ("ENUM", "ENUM"), "oscC.wavetable: expected ENUM strategy, got %r" % (result,)


def test_resolve_obs_type_normal_control_unchanged():
    """Controls with element_kind=CONTROL still return ("NUMERIC", "NUMERIC")."""
    from expected_inventory import resolve_observation_type
    assert resolve_observation_type("oscA.octave") == ("NUMERIC", "NUMERIC")
    assert resolve_observation_type("filter1.cutoff") == ("NUMERIC", "NUMERIC")


# ---------------------------------------------------------------------------
# Class 2: generate() flags — no output_scores in _run_vlm_on_crop / _transcribe_roi
# ---------------------------------------------------------------------------

def _get_crops_dict_keys_and_tuples():
    """Parse _GENERIC_SERUM_UI_CROPS from source via AST, handling both Assign and AnnAssign."""
    import ast
    src = (Path(__file__).parent / "observation_engine.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    keys, crops = set(), {}
    for node in ast.walk(tree):
        # handle both `x = {...}` and `x: Type = {...}`
        target = None
        value = None
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_GENERIC_SERUM_UI_CROPS":
                    target, value = t, node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "_GENERIC_SERUM_UI_CROPS":
                target, value = node.target, node.value
        if target is None or not isinstance(value, ast.Dict):
            continue
        for k, v in zip(value.keys, value.values):
            if isinstance(k, ast.Constant):
                keys.add(k.value)
                if isinstance(v, ast.Tuple):
                    elts = [e.value if isinstance(e, ast.Constant) else None for e in v.elts]
                    crops[k.value] = elts
    return keys, crops


def _get_generate_kwargs_from_source(func_name: str) -> str:
    """Extract the model.generate(...) call line from observation_engine source."""
    src_path = Path(__file__).parent / "observation_engine.py"
    src = src_path.read_text(encoding="utf-8")
    in_func = False
    for line in src.splitlines():
        if ("def %s(" % func_name) in line:
            in_func = True
        if in_func and "model.generate(" in line:
            return line
    return ""


def test_run_vlm_on_crop_no_output_scores():
    """_run_vlm_on_crop must not pass output_scores=True or return_dict_in_generate=True."""
    gen_line = _get_generate_kwargs_from_source("_run_vlm_on_crop")
    assert gen_line, "_run_vlm_on_crop: could not find model.generate() call"
    assert "output_scores" not in gen_line, \
        "_run_vlm_on_crop still passes output_scores=True — corrupts 4-bit greedy decode:\n  %s" % gen_line
    assert "return_dict_in_generate" not in gen_line, \
        "_run_vlm_on_crop still passes return_dict_in_generate=True:\n  %s" % gen_line


def test_transcribe_roi_no_output_scores():
    """_transcribe_roi must not pass output_scores=True or return_dict_in_generate=True."""
    gen_line = _get_generate_kwargs_from_source("_transcribe_roi")
    assert gen_line, "_transcribe_roi: could not find model.generate() call"
    assert "output_scores" not in gen_line, \
        "_transcribe_roi still passes output_scores=True:\n  %s" % gen_line
    assert "return_dict_in_generate" not in gen_line, \
        "_transcribe_roi still passes return_dict_in_generate=True:\n  %s" % gen_line


# ---------------------------------------------------------------------------
# Class 3a: OCT/SEM/FIN/CRS siblings in _GENERIC_SERUM_UI_CROPS
# ---------------------------------------------------------------------------

def test_osc_row_siblings_have_crop_entries():
    """oscA.semitone, oscA.fine, oscA.crs all have entries in _GENERIC_SERUM_UI_CROPS."""
    keys, _ = _get_crops_dict_keys_and_tuples()
    assert "oscA.semitone" in keys, "oscA.semitone missing from _GENERIC_SERUM_UI_CROPS"
    assert "oscA.fine" in keys, "oscA.fine missing from _GENERIC_SERUM_UI_CROPS"
    assert "oscA.crs" in keys, "oscA.crs missing from _GENERIC_SERUM_UI_CROPS"


def test_osc_row_siblings_field_index_correct():
    """Siblings use correct field_index values (1=SEM, 2=FIN, 3=CRS) with field_count=4."""
    _, crops = _get_crops_dict_keys_and_tuples()
    assert crops.get("oscA.semitone", [None]*6)[4] == 1, "oscA.semitone field_index should be 1 (SEM)"
    assert crops.get("oscA.fine", [None]*6)[4] == 2, "oscA.fine field_index should be 2 (FIN)"
    assert crops.get("oscA.crs", [None]*6)[4] == 3, "oscA.crs field_index should be 3 (CRS)"
    assert crops.get("oscA.semitone", [None]*6)[5] == 4, "oscA.semitone field_count should be 4"


# ---------------------------------------------------------------------------
# Class 3b: _locate_control_bbox uses display_name in prompt
# ---------------------------------------------------------------------------

def test_locate_uses_display_name_in_prompt():
    """_locate_control_bbox builds a prompt with the Atlas display_name, not the raw API key."""
    import ast
    src = (Path(__file__).parent / "observation_engine.py").read_text(encoding="utf-8")
    # Find the _locate_control_bbox function source and check it mentions display_name lookup.
    assert "display_name" in src, "_locate_control_bbox must reference Atlas display_name"
    # Verify the Atlas get_control import is inside _locate_control_bbox (not just elsewhere).
    in_func = False
    found_gc = False
    for line in src.splitlines():
        if "def _locate_control_bbox(" in line:
            in_func = True
        if in_func and "def " in line and "_locate_control_bbox" not in line:
            in_func = False  # left function
        if in_func and "get_control" in line:
            found_gc = True
    assert found_gc, "_locate_control_bbox should import/call get_control for display_name lookup"


if __name__ == "__main__":
    tests = [
        test_resolve_obs_type_element_kind_none_continuous,
        test_resolve_obs_type_element_kind_none_enum,
        test_resolve_obs_type_element_kind_none_enum_c,
        test_resolve_obs_type_normal_control_unchanged,
        test_run_vlm_on_crop_no_output_scores,
        test_transcribe_roi_no_output_scores,
        test_osc_row_siblings_have_crop_entries,
        test_osc_row_siblings_field_index_correct,
        test_locate_uses_display_name_in_prompt,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print("PASS", t.__name__)
            passed += 1
        except Exception as e:
            print("FAIL", t.__name__, "—", e)
            failed += 1
    print("\n%d/%d passed" % (passed, passed + failed))
    sys.exit(0 if failed == 0 else 1)
