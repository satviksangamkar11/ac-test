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
    # Serum's untouched-module sentinel ('default' string) vs a dict that gained keys: descend into the keys, not the container
    if isinstance(b, dict) and isinstance(a, str) and not isinstance(a, dict):
        a = {}
    if isinstance(a, dict) and isinstance(b, str):
        b = {}
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


# (PresetSpec model, field) -> where its vocabulary comes from. Reviewed data; every entry cites the upstream table it reads.
VOCAB = {("OscillatorSpec", "warp_mode"): ("dict", "SIMPLE_WARP_MODES"), ("OscillatorSpec", "warp_mode2"): ("dict", "SIMPLE_WARP_MODES"),
         ("OscillatorSpec", "wavetable"): ("dict", "SIMPLE_WAVETABLES"), ("OscillatorSpec", "noise_type"): ("enum", ("NOISEOSC_PARAMS", "kParamNoiseType")),
         ("FilterSpec", "type"): ("dict", "SIMPLE_FILTER_TYPES"), ("LfoSpec", "mode"): ("enum", ("LFO_PARAMS", "kParamMode")),
         ("LfoSpec", "shape"): ("dict", "SIMPLE_LFO_TYPES"), ("ArpSpec", "shape"): ("dict", "SIMPLE_ARP_SHAPES"),
         ("MacroSpec", "name"): ("text", None), ("GlobalSpec", "fx_bus1_destination"): ("literal", None),
         ("GlobalSpec", "fx_bus2_destination"): ("literal", None)}
# fields that only take effect when a COMPANION field is set (differential is empty without it): context patch per field
COMPANION = {"warp_amount2": ("warp_mode2", "fm")}
SAMPLE_FIELDS = {"sample_loop_start", "sample_loop_end", "sample_loop_crossfade"}


def vocab_words(ctrl):
    fi = field_info(ctrl)
    model = LISTS[ctrl["list"]] if ctrl["kind"] == "field" else SINGLETON_DEFAULTS[ctrl["attr"]]
    src = VOCAB.get((model.__name__, ctrl["field"]))
    if src is None:
        return None, None
    kind, ref = src
    if kind == "dict":
        return "enum_str", list(getattr(schema, ref))
    if kind == "enum":
        return "enum_str", list(getattr(schema, ref[0])[ref[1]].enum_values)
    if kind == "literal":
        return "enum_str", [x for t in typing.get_args(fi.annotation) for x in (typing.get_args(t) or (t,)) if isinstance(x, str)]
    return "text", ["QUAL_A", "QUAL_B"]


def sample_wav():
    p = HERE / "contexts" / "qual_sample.wav"
    if not p.exists():
        import math
        import struct
        import wave
        p.parent.mkdir(exist_ok=True)
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 220 * i / 44100))) for i in range(44100)))
    return str(p)


def companion_spec(ctrl):
    """(base spec with the companion fields set, context name) for fields whose effect needs another field; else (None, None)."""
    if ctrl["kind"] != "field" or ctrl["list"] != "oscillators":
        return None, None
    f = ctrl["field"]
    if f in COMPANION:
        cf, cv = COMPANION[f]
        lst = [o.model_copy(update={cf: cv}) if i < 3 else o for i, o in enumerate(base_spec().oscillators)]
        return base_spec().model_copy(update={"oscillators": lst}), "OSC_WARP2"
    if f in SAMPLE_FIELDS:
        wav = sample_wav()
        lst = [o.model_copy(update={"sample_playback_source": wav, "sample_loop": "forward"}) if i < 3 else o for i, o in enumerate(base_spec().oscillators)]
        return base_spec().model_copy(update={"oscillators": lst}), "OSC_SAMPLE"
    return None, None


def diff_for(spec_base, ctrl, v):
    b0 = apply_spec(BASE.data, spec_base)
    b1 = apply_spec(BASE.data, with_field(spec_base, ctrl, v))
    return leaves(b0, b1)


def derive(ctrl):
    """-> dict(mechanism, mutation, domain, context, [spec_patch]) or dict(reason=...). Reads only upstream apply_spec and schema tables."""
    fi = field_info(ctrl)
    lo, hi = bounds(fi)
    t = base_type(fi)
    kind, words = vocab_words(ctrl)
    spec_base, ctx = companion_spec(ctrl)
    spec_base = spec_base or base_spec()
    ctx = ctx or "INIT"
    if kind:                                         # string domains
        table, paths = {}, []
        for w in words:
            try:
                d = diff_for(spec_base, ctrl, w)
            except Exception as e:
                return {"reason": "apply_spec rejected vocabulary word %r: %s" % (w, str(e)[:70])}
            table[w] = [(p, b) for p, a, b in d]
            paths += [tuple(p) for p, _a, _b in d]
        if not any(table.values()):
            return {"reason": "NO_DIFF for any vocabulary word"}
        distinct = {json.dumps([p for p, _ in v]) for v in table.values() if v}
        if len(distinct) == 1 and all(len(v) == 1 for v in table.values() if v):
            path = json.loads(next(iter(distinct)))[0]
            raw = [v[0][1] for v in table.values() if v]
            dflt = [w for w, v in table.items() if not v]
            return {"mechanism": "ENUM_RAW" if kind == "enum_str" else "TEXT_RAW", "context": ctx,
                    "mutation": {"kind": "raw_path", "path": path}, "domain": {"kind": kind, "values": list(dict.fromkeys(raw))},
                    "vocabulary_map": {w: (v[0][1] if v else None) for w, v in table.items()}, "default_words": dflt}
        # primary = the leaf whose value VARIES with the vocabulary word (the semantic leaf); constant leaves are side effects
        cand = {}
        for v in table.values():
            for p, val in v:
                cand.setdefault(json.dumps(p), set()).add(json.dumps(val))
        primary = json.loads(max(cand, key=lambda k: len(cand[k])))
        return {"mechanism": "LEAF_SET", "context": ctx,
                "mutation": {"kind": "leaf_set", "primary": primary, "table": {w: [[list(p), val] for p, val in v] for w, v in table.items()}},
                "domain": {"kind": kind, "values": list(table)}}
    if t not in (bool, int, float):
        return {"reason": "UNSUPPORTED_FIELD_TYPE %r" % (t,)}
    if t is bool:
        vals = [not bool(fi.default), bool(fi.default)]
    else:
        d0 = fi.default if isinstance(fi.default, (int, float)) and not isinstance(fi.default, bool) else 0.0
        vals = test_values(fi, lo, hi) if lo is not None and hi is not None else [d0 + x for x in (1.0, -1.0, 10.0, -10.0, 0.5, -0.5, 100.0, -100.0)]
    tried = []
    for v in vals:
        try:
            d = diff_for(spec_base, ctrl, v)
        except Exception as e:
            tried.append("apply_spec rejected %r" % (v,))
            continue
        if len(d) == 1:
            path = d[0][0]
            dm = {"kind": "bool" if t is bool else ("int" if t is int else "float"), "lo": lo, "hi": hi, "default": fi.default}
            dom = domain_for(dm, path)
            out = {"mechanism": "DIRECT_RAW" if ctx == "INIT" else "CONTEXTUAL_RAW", "context": ctx, "mutation": {"kind": "raw_path", "path": path},
                   "domain": dom or {"kind": "open", "default": fi.default}}
            if dom is None:
                out["mechanism"] = "OPEN_RAW" if ctx == "INIT" else "CONTEXTUAL_OPEN_RAW"
            return out
        tried.append("%d leaves changed for %r" % (len(d), v))
    return {"reason": "NOT_A_SINGLE_LEAF (%s)" % "; ".join(tried[:2]) if tried else "NO_DIFF"}


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


def ctx_def(name, spec_base=None, fx_type=None):
    if fx_type:
        return {"preset_name": "QUAL_" + name, "fx": [{"type": fx_type, "params": {}}]}
    d = {"preset_name": "QUAL_" + name, "fx": []}
    if spec_base is not None:
        d["spec_patch"] = spec_base.model_dump(mode="json")
    return d


def main(manifest_out, accounting_out):
    bt = json.loads(BT.read_text())["controls"]
    params, acct = [], []
    contexts = {"INIT": ctx_def("INIT")}
    for cid, c in sorted(bt.items()):
        if c["kind"] == "fx":
            ft, ctx = c["fx_type"], "FX_" + c["fx_type"]
            pd = schema.FX_PARAMS.get(ft, {}).get(c["param"])
            path = ["FXRack0", "FX", 0, ft, "plainParams", c["param"]]
            if pd is None:
                acct.append({"atlas_id": cid, "family": ctx, "derived": False, "reason": "FX param not in schema.FX_PARAMS"})
                continue
            contexts.setdefault(ctx, ctx_def(ctx, fx_type=ft))
            if pd.kind == "enum":
                dom, mech = {"kind": "enum_str", "values": list(pd.enum_values or [])}, "ENUM_RAW"
            elif pd.kind == "bool":
                dom, mech = {"kind": "bool"}, "DIRECT_RAW"
            elif pd.min is None or pd.max is None:
                dom, mech = {"kind": "open", "default": pd.default}, "OPEN_RAW"
            else:
                dom, mech = {"kind": ("log" if pd.min > 0 and pd.max / pd.min >= 1000 else "signed" if pd.min < 0 < pd.max else "continuous"),
                             "min": float(pd.min), "max": float(pd.max)}, "DIRECT_RAW"
            params.append({"atlas_id": cid, "context": ctx, "mutation": {"kind": "raw_path", "path": path}, "domain": dom, "mechanism": mech,
                           "derivation": "fx unit param (fixed path); domain from schema.FX_PARAMS ParamDef"})
            acct.append({"atlas_id": cid, "family": ctx, "derived": True, "mechanism": mech, "raw_path": path, "domain": dom})
            continue
        fam = c.get("list") or c.get("attr")
        r = derive(c)
        if "reason" in r:
            if "UNSUPPORTED_FIELD_TYPE" in r["reason"]:
                r["reason"] = "VOCABULARY_UNKNOWN (unvalidated string enum: the live dropdown must be read to learn its words)"
            acct.append({"atlas_id": cid, "family": fam, "derived": False, "reason": r["reason"]})
            continue
        if r["context"] not in contexts:
            sb, _ = companion_spec(c)
            contexts[r["context"]] = ctx_def(r["context"], sb)
        entry = {"atlas_id": cid, "context": r["context"], "mutation": r["mutation"], "domain": r["domain"], "mechanism": r["mechanism"],
                 "derivation": "differential of upstream apply_spec on the bound PresetSpec field"}
        for k in ("vocabulary_map", "default_words"):
            if k in r:
                entry[k] = r[k]
        params.append(entry)
        acct.append({"atlas_id": cid, "family": fam, "derived": True, "mechanism": r["mechanism"], "context": r["context"],
                     "raw_path": r["mutation"].get("path") or r["mutation"].get("primary"), "domain": r["domain"]})
    m = {"version": 2, "kind": "bulk_context", "note": 48, "render_sec": 1.0, "bands": [20, 200, 800, 3000, 8000, 20000],
         "min_noise_floor_db": 0.5, "session_size": 30, "contexts": contexts, "parameters": params}
    json.dump(m, open(manifest_out, "w"), indent=1)
    mech, reasons = {}, {}
    for a_ in acct:
        if a_["derived"]:
            mech[a_["mechanism"]] = mech.get(a_["mechanism"], 0) + 1
        else:
            k = a_["reason"].split(" (")[0]
            reasons[k] = reasons.get(k, 0) + 1
    json.dump({"total_candidates": len(bt), "derived": len(params), "not_derived": len(bt) - len(params), "mechanisms": mech,
               "not_derived_reasons": reasons, "authorizes_nothing": True, "candidates": acct}, open(accounting_out, "w"), indent=1)
    print("candidates %d  derived %d  not derived %d" % (len(bt), len(params), len(bt) - len(params)))
    print("mechanisms", json.dumps(mech))
    print("not derived", json.dumps(reasons))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
