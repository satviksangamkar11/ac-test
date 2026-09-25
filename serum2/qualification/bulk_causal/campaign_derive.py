"""Phase 4: derive a bulk-engine manifest for the MCP-mutable candidates from EXISTING evidence -- no name matching, no invention.

    python campaign_derive.py <manifest_out.json> <accounting_out.json>

For every control in serum_mcp_binding_table.json (the 330 Atlas -> serum-mcp bindings):
  * raw mutation path = the leaf that upstream's own apply_spec changes when the bound PresetSpec field is changed (a differential on
    real output bodies; FX unit params use their fixed FXRack0.FX[0].<type>.plainParams.<key> path). A change that touches more than one
    leaf, or none, is NOT derived -- it is reported with its reason, never forced into a scalar path.
  * declared domain = the PresetSpec field's own ge/le bounds, else the schema ParamDef bounds of the raw key. No bounds -> not derived.
  * String enums are NOT derived here (their meaning needs GUI-proven labels): reported as such.
The output is a manifest for bulk_worker.py plus an accounting that names every one of the candidates. Read-only w.r.t. authority files.
"""
import copy
import json
import sys
import typing
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from preset_build import BASE, SPEC0  # noqa: E402
from serum_mcp.generation import spec as S  # noqa: E402
from serum_mcp.preset import schema  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402

BT = ROOT / "serum2" / "reference" / "serum_mcp_binding_table.json"
LISTS = {"oscillators": S.OscillatorSpec, "envelopes": S.EnvelopeSpec, "lfos": S.LfoSpec, "filters": S.FilterSpec, "macros": S.MacroSpec}
SINGLETON_DEFAULTS = {"global_": S.GlobalSpec, "arp": S.ArpSpec, "voice_unison": S.VoiceUnisonSpec}
CONTAINER_SCHEMA = (("Oscillator", "OSCILLATOR_PARAMS"), ("WTOsc", "WTOSC_PARAMS"), ("VoiceFilter", "VOICE_FILTER_PARAMS"), ("Env", "ENV_PARAMS"),
                    ("LFO", "LFO_PARAMS"), ("Macro", "MACRO_PARAMS"), ("Global", "GLOBAL_PARAMS"), ("VoicePanel", "VOICE_PANEL_PARAMS"),
                    ("Arp", "ARP_PARAMS"))


def leaves(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in set(a) | set(b):
            out += leaves(a.get(k), b.get(k), path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [x for i, (u, v) in enumerate(zip(a, b)) for x in leaves(u, v, path + (i,))]
    return [] if a == b else [(list(path), a, b)]


def base_spec():
    upd = {}
    for attr, cls in SINGLETON_DEFAULTS.items():
        if getattr(SPEC0, attr, None) is None:
            upd[attr] = cls()
    return SPEC0.model_copy(update=upd) if upd else SPEC0


def with_field(spec, ctrl, value):
    if ctrl["kind"] == "field":
        lst = list(getattr(spec, ctrl["list"]))
        lst[ctrl["index"]] = lst[ctrl["index"]].model_copy(update={ctrl["field"]: value})
        return spec.model_copy(update={ctrl["list"]: lst})
    obj = getattr(spec, ctrl["attr"])
    if isinstance(obj, dict):
        obj = S.GlobalSpec(**obj)
    return spec.model_copy(update={ctrl["attr"]: obj.model_copy(update={ctrl["field"]: value})})


def field_info(ctrl):
    model = LISTS[ctrl["list"]] if ctrl["kind"] == "field" else SINGLETON_DEFAULTS[ctrl["attr"]]
    return model.model_fields[ctrl["field"]]


def bounds(fi):
    lo = hi = None
    for m in fi.metadata:
        lo = getattr(m, "ge", lo)
        hi = getattr(m, "le", hi)
    return lo, hi


def base_type(fi):
    a = fi.annotation
    args = [t for t in typing.get_args(a) if t is not type(None)]
    return args[0] if args else a


def test_values(fi, lo, hi):
    t = base_type(fi)
    if t is bool:
        return [not bool(fi.default), bool(fi.default)]
    if t in (int, float) and lo is not None and hi is not None:
        d = fi.default if isinstance(fi.default, (int, float)) and not isinstance(fi.default, bool) else lo
        mid = (lo + hi) / 2
        cands = [mid, lo + (hi - lo) * 0.3, hi, lo]
        return [type(t(0))(c) if t is int else float(c) for c in cands if c != d]
    return []


def derive_path(ctrl):
    fi = field_info(ctrl)
    lo, hi = bounds(fi)
    t = base_type(fi)
    if t is str or (typing.get_origin(fi.annotation) is typing.Literal) or t not in (bool, int, float):
        return None, "STRING_OR_COMPLEX_FIELD (enum/label semantics need GUI-proven labels)", None
    vals = test_values(fi, lo, hi)
    if not vals and t is not bool:
        return None, "NO_DECLARED_BOUNDS on the PresetSpec field", None
    b0 = apply_spec(BASE.data, base_spec())
    tried = []
    for v in vals:
        try:
            b1 = apply_spec(BASE.data, with_field(base_spec(), ctrl, v))
        except Exception as e:
            tried.append("apply_spec rejected %r: %s" % (v, str(e)[:80]))
            continue
        d = leaves(b0, b1)
        if len(d) == 1:
            return d[0][0], None, {"kind": "bool" if t is bool else ("int" if t is int else "float"), "lo": lo, "hi": hi, "default": fi.default}
        tried.append("%d leaves changed for %r" % (len(d), v))
    return None, "NOT_A_SINGLE_LEAF (%s)" % "; ".join(tried[:2]) if tried else "NO_DIFF", None


def schema_bounds(path):
    """Fallback: schema ParamDef bounds of the raw key, by container prefix."""
    cont, key = str(path[0]), path[-1]
    for prefix, tname in CONTAINER_SCHEMA:
        if cont.startswith(prefix) or (len(path) > 2 and str(path[1]).startswith(prefix)):
            t = getattr(schema, tname, None)
            if t and key in t:
                pd = t[key]
                return pd.min, pd.max
    return None, None


def domain_for(dm, raw_path):
    if dm["kind"] == "bool":
        return {"kind": "bool", "default": None}
    lo, hi = dm["lo"], dm["hi"]
    if lo is None or hi is None:
        lo, hi = schema_bounds(raw_path)
    if lo is None or hi is None:
        return None
    if dm["kind"] == "int":
        return {"kind": "int", "min": int(lo), "max": int(hi)}
    kind = "log" if lo > 0 and hi / lo >= 1000 else ("signed" if lo < 0 < hi else "continuous")
    return {"kind": kind, "min": float(lo), "max": float(hi)}


def main(manifest_out, accounting_out):
    bt = json.loads(BT.read_text())["controls"]
    params, acct = [], []
    contexts = {"INIT": {"preset_name": "QUAL_INIT", "fx": []}}
    for cid, c in sorted(bt.items()):
        if c["kind"] == "fx":
            ft = c["fx_type"]
            pd = schema.FX_PARAMS.get(ft, {}).get(c["param"])
            ctx = "FX_" + ft
            path = ["FXRack0", "FX", 0, ft, "plainParams", c["param"]]
            if pd is None or pd.kind == "enum" or (pd.kind == "float" and (pd.min is None or pd.max is None)):
                acct.append({"atlas_id": cid, "family": ctx, "derived": False, "reason": "FX param with enum semantics or no schema bounds"})
                continue
            contexts.setdefault(ctx, {"preset_name": "QUAL_" + ctx, "fx": [{"type": ft, "params": {}}]})
            dom = {"kind": "bool"} if pd.kind == "bool" else {"kind": ("log" if pd.min > 0 and pd.max / pd.min >= 1000 else "signed" if pd.min < 0 < pd.max else "continuous"),
                                                              "min": float(pd.min), "max": float(pd.max)}
            params.append({"atlas_id": cid, "context": ctx, "mutation": {"kind": "raw_path", "path": path}, "domain": dom,
                           "derivation": "fx unit param (fixed path); domain from schema.FX_PARAMS ParamDef"})
            acct.append({"atlas_id": cid, "family": ctx, "derived": True, "raw_path": path, "domain": dom})
            continue
        path, reason, dm = derive_path(c)
        fam = c.get("list") or c.get("attr")
        if path is None:
            acct.append({"atlas_id": cid, "family": fam, "derived": False, "reason": reason})
            continue
        dom = domain_for(dm, path)
        if dom is None:
            acct.append({"atlas_id": cid, "family": fam, "derived": False, "reason": "NO_BOUNDS (neither PresetSpec field nor schema ParamDef)", "raw_path": path})
            continue
        params.append({"atlas_id": cid, "context": "INIT", "mutation": {"kind": "raw_path", "path": path}, "domain": dom,
                       "derivation": "differential of upstream apply_spec on the bound PresetSpec field"})
        acct.append({"atlas_id": cid, "family": fam, "derived": True, "raw_path": path, "domain": dom})
    m = {"version": 2, "kind": "bulk_context", "note": 48, "render_sec": 1.0, "bands": [20, 200, 800, 3000, 8000, 20000],
         "min_noise_floor_db": 0.5, "session_size": 30, "contexts": contexts, "parameters": params}
    json.dump(m, open(manifest_out, "w"), indent=1)
    reasons = {}
    for a in acct:
        if not a["derived"]:
            k = a["reason"].split(" (")[0]
            reasons[k] = reasons.get(k, 0) + 1
    json.dump({"total_candidates": len(bt), "derived": len(params), "not_derived": len(bt) - len(params), "not_derived_reasons": reasons,
               "authorizes_nothing": True, "candidates": acct}, open(accounting_out, "w"), indent=1)
    print("candidates %d  derived %d  not derived %d\n%s" % (len(bt), len(params), len(bt) - len(params), json.dumps(reasons, indent=1)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
