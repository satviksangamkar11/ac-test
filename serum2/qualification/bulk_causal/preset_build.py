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
from serum_mcp.preset.packer import SerumPreset, pack_bytes, pack_file, unpack_bytes, unpack_file  # noqa: E402

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


# ---- context-based bulk verification: state construction WITHOUT a preset per observation --------------------------------
def build_context_body(ctx: dict):
    """Canonical base body for a qualification context: init preset + the context's FX units (+ spec_patch). Pure/deterministic.
    ctx = {"fx": [{"type","params"}...], "spec_patch": {...}}"""
    spec = SPEC0
    if ctx.get("spec_patch"):
        spec = type(SPEC0).model_validate(deep_merge(SPEC0.model_dump(), ctx["spec_patch"]))
    units = [FxUnitSpec(type=u["type"], params=dict(u.get("params", {})), wet=u.get("wet", 100.0)) for u in ctx.get("fx", [])]
    return copy.deepcopy(apply_spec(BASE.data, spec.model_copy(update={"fx_chain": units}))), dict(BASE.metadata)


def write_context_preset(name, ctx, out_dir):
    """The ONE persistent preset of a context (written once, reused for every parameter). Returns (path, body, meta)."""
    body, meta = build_context_body(ctx)
    path = os.path.join(out_dir, name + ".SerumPreset")
    os.makedirs(out_dir, exist_ok=True)
    pack_file(SerumPreset(metadata=dict(meta, presetName=name), data=body), path)
    return path, body, meta


def pack_unpack(meta, body):
    return unpack_bytes(pack_bytes(SerumPreset(metadata=meta, data=body))).data
