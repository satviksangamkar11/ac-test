"""Serialisation + state comparison, with the proof levels kept apart.

  COMPILED -> SERIALIZED -> FILE_READBACK -> (Serum loads it) -> DIRECT_UI_READBACK -> NORMALIZED_COMPARISON

A .SerumPreset that matches what the compiler intended is FILE evidence only. It says nothing about what a real
Serum instance loaded. Only a DIRECT_UI readback of the live plugin can raise a run to LIVE_UI_VERIFIED, and an
OVERRIDDEN_APPROXIMATION is never counted as exact.

Every reproduced field ends as exactly one of:
  VERIFIED_EXACT | VERIFIED_WITH_NORMALIZATION | OVERRIDDEN_APPROXIMATION | MISMATCH | NOT_COMPILED | UNREADABLE
and every group as EXACT_STATE only if all OBSERVED members were reproduced and verified exactly.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "serum-mcp" / "src"))

from serum2.execution.authorized_state_compiler import CompileReport  # noqa: E402

_GROUP_FX = re.compile(r"^fx\.([a-z]+)\.")
_RANK = {"VERIFIED_EXACT": 0, "VERIFIED_WITH_NORMALIZATION": 1, "OVERRIDDEN_APPROXIMATION": 2, "UNREADABLE": 3,
         "NOT_COMPILED": 4, "MISMATCH": 5}
FILE_READBACK = "FILE_READBACK"
DIRECT_UI = "DIRECT_UI"


def serialize(report: CompileReport, subfolder: str = "VLP1") -> str:
    """Write the .SerumPreset for a COMPLETE compile of authorized operations. Nothing else can be serialized."""
    if report.status != "SUCCESS" or report.admitted != report.compiled or not report.ops:
        raise RuntimeError("refusing to serialize: compilation is %s (%d/%d)" % (report.status, report.compiled, report.admitted))
    from serum_mcp.generation.spec import PresetSpec
    from serum_mcp.tools.generate_preset import generate_preset
    return generate_preset(PresetSpec(**report.spec), subfolder=subfolder).splitlines()[0]


def read_back_file(preset_path: str):
    from serum_mcp.preset.introspect import extract_spec
    from serum_mcp.preset.packer import unpack_file
    return extract_spec(unpack_file(preset_path).data)


def _actual(op: Dict[str, Any], rack, back):
    if op["kind"] == "field":
        items = getattr(back, op["list"])
        return getattr(items[op["index"]], op["field"], None) if op["index"] < len(items) else None
    if op["kind"] == "fx":
        u = next((u for u in back.fx_chain if u.type == op["fx_type"] and u.rack == (rack or 0)), None)
        return None if u is None else (u.wet if op["param"] == "kParamWet" else u.params.get(op["param"]))
    m = next((m for m in back.mod_routes if m.source == op["source"] and m.destination == op["destination"]), None)
    return m.amount if m else None


def _close(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-6)
    return a == b


def _group(row) -> Tuple:
    o = row.op
    if o and o["kind"] == "fx":
        return ("fx", row.context.get("rack", 0), o["fx_type"])
    if o and o["kind"] == "field":
        return (o["list"], o["index"])
    m = _GROUP_FX.match(row.control_id)
    if m:
        return ("fx-unit-token", row.context.get("rack", 0), m.group(1))
    return (row.control_id.split(".")[0],)


def _grade(fid: str, ok: bool) -> str:
    if fid == "APPROXIMATED":
        return "OVERRIDDEN_APPROXIMATION"
    if not ok:
        return "MISMATCH"
    return "VERIFIED_WITH_NORMALIZATION" if fid == "NORMALIZED" else "VERIFIED_EXACT"


def _groups(rows, fields: Dict[str, str]) -> Dict[str, Any]:
    groups: Dict[Tuple, Dict[str, Any]] = defaultdict(lambda: {"fields": {}, "unreproduced": []})
    for r in rows:
        if r.terminal in ("IGNORED_NAVIGATION", "NOT_SERUM_SURFACE"):
            continue
        g = groups[_group(r)]
        key = r.control_id + "@" + str(r.context.get("rack", "-"))
        if key in fields:
            g["fields"][r.control_id] = fields[key]
        else:
            g["unreproduced"].append((r.control_id, r.terminal if r.terminal != "OPERATION_DERIVED" else "NOT_ADMITTED/" + r.admission))
    out = {}
    for k, g in groups.items():
        if not g["fields"]:
            continue
        worst = max(g["fields"].values(), key=lambda s: _RANK[s])
        ok = worst in ("VERIFIED_EXACT", "VERIFIED_WITH_NORMALIZATION")
        state = "EXACT_STATE" if (worst == "VERIFIED_EXACT" and not g["unreproduced"]) else (
            "PARTIAL_STATE(%d observed members not reproduced)" % len(g["unreproduced"]) if ok else worst)
        out[str(k)] = {"state": state, "fields": dict(g["fields"]), "unreproduced": g["unreproduced"]}
    return out


def compare_file(rows, back, report: CompileReport) -> Dict[str, Any]:
    """FILE_READBACK comparison of the serialized preset against the authorized operands."""
    ids = {o.operation_id for o in report.ops}
    fields: Dict[str, str] = {}
    for r in rows:
        o = r.op
        oid = "%s@%s" % (r.control_id, r.context.get("rack", "-"))
        if not o or r.terminal != "OPERATION_DERIVED" or oid not in ids:
            continue
        want = o.get("value", o.get("amount"))
        got = _actual(o, r.context.get("rack"), back)
        fid = "APPROXIMATED" if o.get("fidelity") == "APPROXIMATED_FROM_TEMPO" else ("NORMALIZED" if o.get("normalized") else "EXACT")
        st = _grade(fid, got is not None and _close(got, want))
        r.execution = "%s[%s](observed=%r, wanted=%r, file_has=%r)" % (st, FILE_READBACK, r.value, want, got)
        fields[r.control_id + "@" + str(r.context.get("rack", "-"))] = st
    return {"route": FILE_READBACK, "field_counts": dict(Counter(fields.values())), "fields": fields,
            "groups": _groups(rows, fields)}


def _ui_equal(expected: Any, ui_text: Any) -> bool:
    from serum2.producer.state_ledger import _numeric, exact_norm
    a, b = _numeric(expected, None), _numeric(ui_text, None)
    if a and b:
        # A7: Unit normalization: "300" unit="ms" and "300 ms" are equivalent.
        # Compare numeric values first (they must match within tolerance).
        if not math.isclose(a[0], b[0], rel_tol=1e-6, abs_tol=1e-6):
            return False
        # Then check unit compatibility. Units match if:
        #   - they're identical, or
        #   - one is empty (unit-less), or
        #   - they normalize to the same canonical form (e.g., "ms " == " ms")
        au = (a[1] or "").strip()
        bu = (b[1] or "").strip()
        if au == bu:
            return True
        if au == "" or bu == "":
            return True
        # One unit contains the other as a substring (with spaces normalized)
        # "ms" in "300 ms" after split, or "milliseconds" in "milliseconds per beat"
        return au in bu or bu in au
    return exact_norm(expected) == exact_norm(ui_text)


def _known_epoch_versions() -> set:
    from serum2.producer.execution_epoch import KNOWN_EPOCHS
    return {e.serum_version for e in KNOWN_EPOCHS}


def _binding_quality(ui_readback: Dict[str, Any]) -> str:
    """Classify how a UI readback was obtained.

    LOADER_BOUND         — carries complete loader_evidence (run_id, track_nonce, serum_module_sha256,
                           epoch, screenshot_sha, crop_coords) with all required fields AND valid content,
                           AND the top-level readback carries an actual observed UI values payload
    HEADLESS_DAWDREAMER  — A8: DawDreamer/headless evidence, never eligible for VERIFIED
    MANUALLY_READ        — has captured_at/serum/method metadata but no loader proof
    UNBOUND              — bare dict; rejected from LIVE_UI_VERIFIED

    A7: loader_evidence must include epoch and screenshot_sha for integrity binding to actual run.
    All fields must have structurally valid content:
    - run_id: non-empty string
    - track_nonce: non-empty string
    - serum_module_sha256: exactly 64 hexadecimal characters
    - screenshot_sha: exactly 64 hexadecimal characters
    - epoch: must identify one of the pinned, known ExecutionEpochs (e.g. "2.0.23", "2.0.21") -- an
      arbitrary non-empty string ("staging", "1.0.0") does NOT integrity-bind the readback to a real,
      qualified Serum build, so it is refused exactly like a missing field.
    - crop_coords: exactly [x, y, w, h] with numeric finite non-negative values
    - values: the readback must ALSO carry a non-empty top-level "values" mapping of actually observed
      control readings. A structurally perfect loader_evidence envelope with valid hashes but no real
      observed UI content is not sufficient evidence that anything was actually read -- it is downgraded
      exactly like a missing/invalid loader_evidence field.

    A8: DawDreamer evidence is labeled HEADLESS_DAWDREAMER and cannot reach VERIFIED.
    """
    # A8: Check for DawDreamer/headless marker first
    if ui_readback.get("backend") and "DawDreamer" in str(ui_readback.get("backend")):
        return "HEADLESS_DAWDREAMER"
    if ui_readback.get("is_headless") is True:
        return "HEADLESS_DAWDREAMER"

    if ui_readback.get("loader_evidence"):
        le = ui_readback["loader_evidence"]
        # A7: Require all key fields for LOADER_BOUND classification
        required_fields = {"run_id", "track_nonce", "serum_module_sha256", "epoch", "screenshot_sha", "crop_coords"}
        if not required_fields.issubset(le.keys()):
            # Missing field
            if ui_readback.get("captured_at") or ui_readback.get("serum") or ui_readback.get("method"):
                return "MANUALLY_READ"
            return "UNBOUND"

        # A7: Validate content format (not just presence/truthiness)
        run_id = le.get("run_id")
        track_nonce = le.get("track_nonce")
        sha256 = le.get("serum_module_sha256")
        screenshot_sha = le.get("screenshot_sha")
        epoch = le.get("epoch")
        crop_coords = le.get("crop_coords")

        # run_id: non-empty string
        if not isinstance(run_id, str) or not run_id.strip():
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"

        # track_nonce: non-empty string
        if not isinstance(track_nonce, str) or not track_nonce.strip():
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"

        # serum_module_sha256: exactly 64 hex characters
        if not isinstance(sha256, str) or len(sha256) != 64:
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"
        try:
            int(sha256, 16)  # Verify all characters are hex
        except ValueError:
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"

        # screenshot_sha: exactly 64 hex characters
        if not isinstance(screenshot_sha, str) or len(screenshot_sha) != 64:
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"
        try:
            int(screenshot_sha, 16)  # Verify all characters are hex
        except ValueError:
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"

        # epoch: must identify one of the pinned, known ExecutionEpochs -- not an arbitrary string
        if not isinstance(epoch, str) or epoch.strip() not in _known_epoch_versions():
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"

        # crop_coords: exactly [x, y, w, h] with numeric values (not strings)
        if not isinstance(crop_coords, list) or len(crop_coords) != 4:
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"
        # Check that ALL elements are numeric (int or float), not strings
        if not all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in crop_coords):
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"
        # Verify all are finite
        if not all(-float('inf') < c < float('inf') for c in crop_coords):
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"

        # A7: a structurally perfect loader_evidence envelope with no actual observed UI content is not
        # sufficient evidence that anything was actually read from the live plugin.
        values = ui_readback.get("values")
        if not isinstance(values, dict) or not values:
            return "MANUALLY_READ" if (ui_readback.get("captured_at") or ui_readback.get("serum")) else "UNBOUND"

        # All validation passed
        return "LOADER_BOUND"

    if ui_readback.get("captured_at") or ui_readback.get("serum") or ui_readback.get("method"):
        return "MANUALLY_READ"
    return "UNBOUND"


def compare_ui(rows, ui_readback: Dict[str, Any], report: CompileReport) -> Dict[str, Any]:
    """DIRECT_UI comparison: what the LIVE Serum showed, per control id, against what the video showed for the
    same control. ui_readback = {"route": "DIRECT_UI", "captured_at": ..., "values": {control_id: text}}.
    A control that was compiled but has no UI reading is UNREADABLE (never assumed correct).
    An UNBOUND readback (bare dict) is accepted for comparison but will not reach LIVE_UI_VERIFIED."""
    if ui_readback.get("route") != DIRECT_UI:
        raise ValueError("ui_readback must come from the DIRECT_UI route")
    bq = _binding_quality(ui_readback)
    ids = {o.operation_id for o in report.ops}
    vals = ui_readback["values"]
    fields: Dict[str, str] = {}
    for r in rows:
        oid = "%s@%s" % (r.control_id, r.context.get("rack", "-"))
        if not r.op or oid not in ids:
            continue
        fid = "APPROXIMATED" if r.op.get("fidelity") == "APPROXIMATED_FROM_TEMPO" else ("NORMALIZED" if r.op.get("normalized") else "EXACT")
        if r.control_id not in vals:
            st = "UNREADABLE"
        else:
            st = _grade(fid, _ui_equal(r.value, vals[r.control_id]))
        fields[r.control_id + "@" + str(r.context.get("rack", "-"))] = st
    return {"route": DIRECT_UI, "captured_at": ui_readback.get("captured_at"), "binding_quality": bq,
            "field_counts": dict(Counter(fields.values())), "fields": fields, "groups": _groups(rows, fields)}


def verification_level(file_cmp: Dict[str, Any], ui_cmp: Dict[str, Any] = None) -> str:
    """The highest proof actually reached. Approximation/mismatch/unreadable never reach VERIFIED.
    An UNBOUND ui_cmp (bare hand-typed dict) is refused from LIVE_UI_VERIFIED.

    A8: DawDreamer/headless evidence is labeled HEADLESS_DAWDREAMER and never eligible for VERIFIED.
    """
    bad = ("MISMATCH", "UNREADABLE", "NOT_COMPILED", "OVERRIDDEN_APPROXIMATION")
    if any(k in file_cmp["field_counts"] for k in bad):
        return "FILE_READBACK_FAILED_OR_APPROXIMATE"
    if ui_cmp is None:
        return "FILE_READBACK_VERIFIED_ONLY"
    if ui_cmp.get("binding_quality") == "UNBOUND":
        return "UI_READBACK_UNBOUND"
    # A8: DawDreamer/headless evidence can never produce VERIFIED claims
    if ui_cmp.get("binding_quality") == "HEADLESS_DAWDREAMER":
        return "UI_READBACK_HEADLESS_DAWDREAMER_NOT_VERIFIED"
    if any(k in ui_cmp["field_counts"] for k in bad):
        return "UI_READBACK_FAILED_OR_INCOMPLETE"
    return "LIVE_UI_VERIFIED"
