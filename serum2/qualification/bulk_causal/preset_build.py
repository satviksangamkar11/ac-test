"""Preset construction shared by the causal worker and the GUI preparer (pure serum-mcp; no Serum, no old-repo imports).

`expand` resolves a test's context + auto Range Test Plan; `write_preset` builds the preset with the candidate key set RAW so
out-of-schema probes can reach Serum (and records whether serum-mcp's own validator would have accepted the value).
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "vendor", "serum-mcp", "src"))
sys.path.insert(1, HERE)
from range_plan import plan as range_plan  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.introspect import extract_spec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset, pack_file, unpack_file  # noqa: E402

BASE = unpack_file(os.path.join(REPO, "vendor", "serum-mcp", "fixtures", "init_preset.SerumPreset"))
SPEC0 = extract_spec(BASE.data)


def deep_merge(a, b):
    for k, v in b.items():
        a[k] = deep_merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a


def write_preset(name, test, value, work, reference=False):
    """Build the preset with the candidate key set RAW (bypassing serum-mcp's own validator so out-of-schema probes can
    reach Serum). Returns (path, mcp_validator_accepts): whether apply_spec itself would have accepted this value."""
    unit = copy.deepcopy(test["unit"])
    params = unit.get("reference_params", unit.get("params", {})) if reference else unit.get("params", {})
    kp = test["candidate"]["kparam"]
    spec = SPEC0
    if test.get("spec_patch"):
        spec = type(SPEC0).model_validate(deep_merge(SPEC0.model_dump(), test["spec_patch"]))

    def build(p):
        fx = FxUnitSpec(type=unit["type"], params=p, wet=unit.get("wet", 100.0))
        return apply_spec(BASE.data, spec.model_copy(update={"fx_chain": [fx]}))

    data = build({k: v for k, v in params.items() if k != kp})
    accepts = True
    if value is not None:
        try:
            build({**params, kp: value})
        except Exception:
            accepts = False
        data["FXRack0"]["FX"][unit.get("index", 0)][unit["type"]]["plainParams"][kp] = value
    path = os.path.join(work, name + ".SerumPreset")
    pack_file(SerumPreset(metadata=BASE.metadata, data=data), path)
    return path, accepts


def expand(test, cfg):
    """Resolve `context` (shared base unit/spec_patch) and auto-generate the value vector from `domain` (Range Test Plan)."""
    t = copy.deepcopy(test)
    ctx = (cfg.get("contexts") or {}).get(t.get("context"))
    if ctx:
        u = deep_merge(copy.deepcopy(ctx.get("unit", {})), t.get("unit", {}))
        u["params"] = {**ctx.get("unit", {}).get("params", {}), **t.get("unit", {}).get("params", {})}
        t["unit"] = u
        t["spec_patch"] = deep_merge(copy.deepcopy(ctx.get("spec_patch", {})), t.get("spec_patch", {})) or None
    d = t.get("domain")
    if d:
        p = range_plan(d)
        t.setdefault("values", p["values"])
        t.setdefault("probe_values", p["probes"])
        if d.get("default") is not None:
            t["candidate"].setdefault("default", d["default"])
    return t
