"""State ledger: every control Stage-A observed gets exactly one terminal outcome.

Observation must never disappear. It may become IGNORED / UNREADABLE / UNRESOLVED /
UNBOUND / UNSUPPORTED / OPERATION_DERIVED -- never nothing. Nothing here is keyed to a
specific video: identity comes from the Atlas, targets and value domains from serum-mcp's
own PresetSpec models and parameter catalog, and value matching is token-based.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "D:/serum-mcp/src")
from serum2.reference.serum_atlas import normalize_control, get_control, EXACT, ALIAS  # noqa: E402

UNREADABLE_FINAL = "UNREADABLE_AFTER_RETRY"
IGNORED_NAVIGATION = "IGNORED_NAVIGATION"
NOT_SERUM_SURFACE = "NOT_SERUM_SURFACE"
UNREADABLE = "UNREADABLE_RE_READ_REQUIRED"
UNRESOLVED = "REFUSED_UNRESOLVED_REFERENCE"
UNBOUND = "UNBOUND_TO_SERUM_PARAM"
UNSUPPORTED = "UNSUPPORTED_VALUE"
DERIVED = "OPERATION_DERIVED"
NAV_TYPES = {"tab", "badge_count"}


@dataclass
class Row:
    control_id: str
    value: Any
    unit: Optional[str]
    status: str
    control_type: str
    source_ts: float
    n_readings: int
    changed_from_previous: bool
    context: Dict[str, Any] = field(default_factory=dict)
    terminal: Optional[str] = None
    reason: str = ""
    op: Optional[Dict[str, Any]] = None
    admission: str = "NOT_EVALUATED"
    execution: str = "NOT_EXECUTED"
    history: List[Tuple[float, Any, str]] = field(default_factory=list)
    read_quality: str = "DIRECT_LAST_READING"


def build_ledger(stage_a: Dict[str, Any]) -> List[Row]:
    """One row per (control_id, fx rack) from the FULL observation set, not from diffs."""
    rows: Dict[Tuple[str, Any], Row] = {}
    for fr in stage_a["frames"]:
        bus = next((c["value"] for c in fr["controls"] if c["control_id"] == "fx.bus_tabs"), None)
        for c in fr["controls"]:
            rack = _rack(bus) if c["control_id"].startswith("fx.") else None
            key = (c["control_id"], rack)
            prev = rows.get(key)
            row = Row(c["control_id"], c["value"], c.get("unit"), c["status"], c["control_type"],
                      fr["timestamp_sec"], (prev.n_readings + 1) if prev else 1,
                      bool(prev and (prev.value != c["value"] or prev.changed_from_previous)),
                      {"rack": rack} if rack is not None else {})
            row.history = (prev.history if prev else []) + [(fr["timestamp_sec"], c["value"], c["status"])]
            rows[key] = row
    for row in rows.values():
        last_ok = next(((t, v) for t, v, st in reversed(row.history) if v is not None and st == "OBSERVED"), None)
        if row.value is None or row.status != "OBSERVED":
            row.read_quality = "UNREADABLE_LATEST" if not last_ok else "STALE_RISK_LAST_KNOWN_NOT_USED"
            if last_ok:
                row.context["last_known_value"], row.context["last_known_ts"] = last_ok[1], last_ok[0]
        else:
            row.read_quality = "DIRECT_LAST_READING"
    return list(rows.values())


def _rack(bus: Optional[str]) -> int:
    m = re.search(r"(\d)", bus or "")
    return int(m.group(1)) if m else 0


def observed_route_rows(stage_a: Dict[str, Any]) -> List[Row]:
    routes: Dict[Tuple[str, str], Row] = {}
    for fr in stage_a["frames"]:
        for r in fr["mod_routes"]:
            k = (r["source"], r["destination"])
            amt = r["amount"] if r["amount"] is not None else (routes[k].value if k in routes else None)
            routes[k] = Row("route:%s->%s" % k, amt, None, r["status"], "route", fr["timestamp_sec"],
                            (routes[k].n_readings + 1) if k in routes else 1, False,
                            {"source": r["source"], "destination": r["destination"], "bipolar": r.get("bipolar"),
                             "transient": "tooltip" in (r.get("note") or "").lower() or (routes[k].context.get("transient") if k in routes else False)})
    return list(routes.values())


# --- generic token matching (no per-control tables) -------------------------------------

_SYN = {"type": "mode", "mode": "type", "reso": "res", "resonance": "res", "q": "reso", "frequency": "freq",
        "level": "volume", "mix": "wet", "dly": "delay", "cutoff": "freq", "gain": "makeup", "bpm": "beatsync",
        "thresh": "threshold", "threshold": "thresh"}
_SIDE = {"left": "1", "low": "1", "right": "2", "high": "2"}


def _tokens(s: Any) -> List[str]:
    s = str(s)
    if re.match(r"^k[A-Z]", s):
        s = s[1:]
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Za-z])(\d)", r"\1 \2", s)
    t = [w.lower() for w in re.split(r"[^A-Za-z0-9]+", s) if w]
    t = [{"low": "l", "high": "h"}.get(w, w) for w in t]
    out: List[str] = []
    for w in t:
        if out and w.isdigit() and len(out[-1]) == 1 and out[-1].isalpha():
            out[-1] += w
        else:
            out.append(w)
    return sorted(out)


def match_enum(observed: Any, domain: List[str]) -> Optional[str]:
    o = _tokens(observed)
    exact = [d for d in domain if _tokens(d) == o]
    if len(exact) == 1:
        return exact[0]
    sub = [d for d in domain if _tokens(d) and set(_tokens(d)) <= set(o)]
    if len(sub) == 1:
        return sub[0]
    best = max(sub, key=lambda d: len(_tokens(d)), default=None) if sub else None
    return best if best and sum(len(_tokens(d)) == len(_tokens(best)) for d in sub) == 1 else None


def _norm_param(p: str) -> str:
    p = re.sub(r"^kParam", "", p).lower().replace("_", "")
    return p


def _param_key(param: str, keys: List[str]) -> Optional[str]:
    """Match an observed param name to a catalog key: original words first, then synonyms;
    left/right style side tokens become a trailing index (left_freq -> freq1)."""
    words = [w for w in re.split(r"[_.]", param.lower()) if w]
    side = next((_SIDE[w] for w in words if w in _SIDE), "")
    base = [w for w in words if w not in _SIDE]
    norm = {k: _norm_param(k) for k in keys}
    for ws in (base, [_SYN.get(w, w) for w in base]):
        stem = "".join(ws)
        for k, n in norm.items():
            if n == stem + side:
                return k
        hits = [k for k, n in norm.items() if n.startswith(stem) and n.endswith(side) and 0 <= len(n) - len(stem) - len(side) <= 2 and len(stem) >= 2]
        if len(hits) == 1:
            return hits[0]
    return None


def _fx_type(unit: str, type_ids: List[str]) -> Optional[str]:
    u = unit.lower()
    scored = []
    for t in type_ids:
        n = t[2:].lower()
        share = len(_common_prefix(u, n))
        if share >= 2 and (u.startswith(n[:share]) and n.startswith(u[:share])):
            scored.append((share, t))
    scored.sort(reverse=True)
    return scored[0][1] if scored and (len(scored) == 1 or scored[0][0] > scored[1][0]) else None


def _common_prefix(a: str, b: str) -> str:
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return a[:i]


# --- value coercion ----------------------------------------------------------------------

_NUM = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(ms|s|hz|khz|db|%|:1)?\s*$", re.I)
_UNIT_ALIAS = {"s": "seconds", "sec": "seconds", ":1": "ratio:1"}
_NOTE = re.compile(r"^\s*(\d+)/(\d+)\s*$")


def _numeric(value: Any, unit: Optional[str]) -> Optional[Tuple[float, str]]:
    m = _NUM.match(str(value))
    if not m:
        return None
    return float(m.group(1)), (m.group(2) or (unit or "")).lower()


def _to_target_unit(num: float, unit: str, target_unit: str, lo: Optional[float], hi: Optional[float],
                    tempo: Optional[float]) -> Tuple[Optional[float], str]:
    tu = _UNIT_ALIAS.get((target_unit or "").lower(), (target_unit or "").lower())
    unit = _UNIT_ALIAS.get(unit, unit)
    if unit == tu or not unit:
        return num, ""
    if unit == "db" and num == 0.0 and (lo, hi) == (0.0, 1.0):
        return 1.0, ""
    conv = {("ms", "seconds"): num / 1000.0, ("ms", "s"): num / 1000.0, ("khz", "hz"): num * 1000.0,
            ("s", "ms"): num * 1000.0}.get((unit, tu))
    if conv is not None:
        return conv, ""
    if unit == "db" and lo is not None and hi is not None and (lo, hi) == (0.0, 1.0) and tu in ("", "normalized", "linear"):
        return None, "dB -> normalized 0..1 has no calibrated mapping"
    if unit == "%" and hi is not None and hi <= 1.0:
        return num / 100.0, ""
    if unit == "%" and tu in ("%", "percent", ""):
        return num, ""
    return None, "no conversion %s -> %s" % (unit, target_unit or "unitless")


def _clamp_check(v: float, lo: Optional[float], hi: Optional[float]) -> Optional[str]:
    if lo is not None and v < lo:
        return "value %s below serum-mcp minimum %s" % (v, lo)
    if hi is not None and v > hi:
        return "value %s above serum-mcp maximum %s" % (v, hi)
    return None


def _field_range(fi) -> Tuple[Optional[float], Optional[float]]:
    lo = hi = None
    for m in fi.metadata:
        lo = getattr(m, "ge", lo)
        hi = getattr(m, "le", hi)
    return lo, hi


# --- catalog access ---------------------------------------------------------------------

_CATALOG: Dict[str, Any] = {}


def catalog() -> Dict[str, Any]:
    if not _CATALOG:
        from serum_mcp.tools.list_parameters import list_parameters
        r = list_parameters()
        _CATALOG.update(json.loads(r) if isinstance(r, str) else r)
    return _CATALOG


def _domain(fieldname: str, module: str, annotation_desc: str) -> Optional[List[str]]:
    from serum_mcp.preset import schema as s
    if fieldname == "warp_mode":
        return list(s.SIMPLE_WARP_MODES)
    if fieldname == "wavetable":
        return list(s.SIMPLE_WAVETABLES)
    if fieldname == "type" and module == "filter":
        return list(s.SIMPLE_FILTER_TYPES) + list(catalog()["voice_filter"]["kParamType"]["enum_values"])
    if fieldname == "noise_type":
        return catalog()["noise_oscillator"]["kParamNoiseType"]["enum_values"]
    if fieldname == "shape":
        return ["random_sh", "rossler", "lorenz", "path"]
    if fieldname == "mode" and module == "lfo":
        return ["Free", "Retrig", "Envelope"]
    m = re.search(r"one of:? ([^.]+)", annotation_desc or "")
    return [x.strip(" '\"") for x in m.group(1).split(",")] if m else None


# --- binding + operation derivation ------------------------------------------------------

_INST = re.compile(r"^(osc|filter|env|lfo)(?:([A-C])|(\d+))\.(.+)$")
_SPECIAL_OSC = {"oscNoise": 3, "sub": 4}


def derive(row: Row, tempo: Optional[float]) -> None:
    from serum_mcp.generation import spec as S
    cid = row.control_id
    if row.control_type in NAV_TYPES:
        row.terminal, row.reason = IGNORED_NAVIGATION, "control_type=%s (UI navigation)" % row.control_type
        return
    res = normalize_control(cid)
    if res.status not in (EXACT, ALIAS):
        top = cid.split(".")[0]
        from serum2.reference.serum_atlas import all_control_ids
        known = {i.split(".")[0] for i in all_control_ids()}
        if top not in known:
            row.terminal, row.reason = NOT_SERUM_SURFACE, "namespace %r not a Serum module in Atlas" % top
        else:
            row.terminal, row.reason = UNRESOLVED, "Atlas status=%s" % res.status
        return
    if row.value is None or str(row.value).strip() in ("", "-") or row.status != "OBSERVED":
        row.terminal, row.reason = UNREADABLE, "value=%r status=%s; targeted re-read required" % (row.value, row.status)
        return
    atlas = get_control(res.canonical_id)
    target = _bind(cid, res.canonical_id, S)
    if target is None:
        row.terminal, row.reason = UNBOUND, "no serum-mcp spec field/param matches this control"
        return
    if target["kind"] == "field" and (target["field"] is None or _domain_miss(target, row.value, S)):
        if not _alt_field(target, row.value, S):
            if target["field"] is None:
                row.terminal, row.reason = UNBOUND, "no serum-mcp spec field matches this control by name or by value domain"
                return
    row.op = target
    err = _coerce(row, target, atlas, tempo)
    if err:
        row.terminal, row.reason, row.op = UNSUPPORTED, err, {**target, "blocked": err}
    else:
        row.terminal = DERIVED


def _bind(cid: str, canon: str, S) -> Optional[Dict[str, Any]]:
    m = _INST.match(cid)
    if m or cid.split(".")[0] in _SPECIAL_OSC:
        if m:
            kind, letter, num, param = m.groups()
            idx = (ord(letter) - 65) if letter else int(num) - 1
        else:
            kind, idx, param = "osc", _SPECIAL_OSC[cid.split(".")[0]], cid.split(".", 1)[1]
        model, listname = {"osc": (S.OscillatorSpec, "oscillators"), "filter": (S.FilterSpec, "filters"),
                           "env": (S.EnvelopeSpec, "envelopes"), "lfo": (S.LfoSpec, "lfos")}[kind]
        if param in ("enable", "enabled"):
            param = "enabled"
        fields = list(model.model_fields)
        f = _param_key(param, fields)
        f = f if f in fields else None
        return {"kind": "field", "list": listname, "index": idx, "field": f, "module": kind, "model": model.__name__}
    if cid.startswith("fx."):
        cat = catalog()
        type_ids = list(cat["fx_type_ids"].values()) if isinstance(cat["fx_type_ids"], dict) else cat["fx_type_ids"]
        unit, _, param = cid[3:].partition(".")
        t = _fx_type(unit, type_ids)
        if t is None:
            return None
        keys = list(cat["fx_params"].get(t, {}))
        k = _param_key(param, keys) if param else None
        return {"kind": "fx", "fx_type": t, "param": k, "observed_param": param}
    return None


def _domain_miss(t: Dict[str, Any], value: Any, S) -> bool:
    fi = getattr(S, t["model"]).model_fields[t["field"]]
    dom = _domain(t["field"], t["module"], fi.description)
    return bool(dom and "str" in str(fi.annotation) and match_enum(str(value), dom) is None)


def _alt_field(t: Dict[str, Any], value: Any, S) -> bool:
    """Name matching failed (or the value is outside that field's domain): find the sibling
    field of the same module whose enum domain actually contains the observed value."""
    for fname, fi in getattr(S, t["model"]).model_fields.items():
        dom = _domain(fname, t["module"], fi.description)
        if dom and "str" in str(fi.annotation) and match_enum(str(value), dom) is not None:
            t["field"] = fname
            return True
    return False


def _coerce(row: Row, t: Dict[str, Any], atlas, tempo: Optional[float]) -> Optional[str]:
    from serum_mcp.generation import spec as S
    v = str(row.value).strip()
    if t["kind"] == "field":
        fi = getattr(S, t["model"]).model_fields[t["field"]]
        ann = str(fi.annotation)
        if "bool" in ann:
            if v.lower() in ("on", "true", "yes"):
                t["value"] = True
            elif v.lower() in ("off", "false", "no"):
                t["value"] = False
            else:
                return "non-boolean %r for boolean field" % v
            t["operation"] = "TOGGLE_ON" if t["value"] else "TOGGLE_OFF"
            return None
        dom = _domain(t["field"], t["module"], fi.description)
        if dom and "str" in ann:
            hit = match_enum(v, dom)
            if hit is None:
                if t["field"] == "mode" and t["module"] == "lfo":
                    return "value %r not in %s" % (v, dom)
                return "value %r has no equivalent in serum-mcp vocabulary %s" % (v, dom[:12])
            t["value"], t["operation"], t["normalized"] = hit, "SELECT", (hit.lower() != v.lower())
            return None
        n = _numeric(v, row.unit)
        if n is None:
            return "value %r is not numeric for field %s" % (v, t["field"])
        lo, hi = _field_range(fi)
        tu = "seconds" if "seconds" in (fi.description or "").lower() else ""
        val, why = _to_target_unit(n[0], n[1], tu, lo, hi, tempo)
        if val is None:
            return why
        bad = _clamp_check(val, lo, hi)
        if bad:
            return bad
        t["value"], t["operation"], t["normalized"] = val, "SET", (val != n[0])
        return None
    p = catalog()["fx_params"][t["fx_type"]].get(t["param"]) if t["param"] else None
    if p is None:
        t["operation"] = "ADD_FX_UNIT"
        return "unit %s recognized, but parameter %r has no catalog key" % (t["fx_type"], t["observed_param"])
    if p["kind"] == "enum":
        hit = match_enum(v, p["enum_values"])
        if hit is None:
            return "value %r not in %s vocabulary" % (v, t["fx_type"])
        t["value"], t["operation"], t["normalized"] = hit, "SELECT", (hit.lower() != v.lower())
        return None
    if p["kind"] == "bool":
        if v.lower() not in ("on", "off"):
            return "non-boolean %r" % v
        t["value"], t["operation"] = v.lower() == "on", "SET"
        return None
    note = _NOTE.match(v)
    if note and p.get("unit") in ("seconds", "s") and tempo:
        t["value"], t["operation"], t["fidelity"] = 240.0 / tempo * int(note.group(1)) / int(note.group(2)), "SET", "APPROXIMATED_FROM_TEMPO"
        return _clamp_check(t["value"], p.get("min"), p.get("max"))
    n = _numeric(v, row.unit)
    if n is None:
        return "value %r is non-numeric but catalog kind=%s carries no enum encoding for %s.%s" % (v, p["kind"], t["fx_type"], t["param"])
    if p["kind"] != "float":
        return "catalog kind %r not expressible from observation" % p["kind"]
    if p.get("unit") == "normalized" and n[1] not in ("",):
        return "%s value has no calibrated mapping to serum-mcp normalized range" % (n[1] or "raw")
    if p.get("unit") == "normalized" and p.get("max") == 1.0 and n[0] > 1.0:
        return "raw value %s has no calibrated mapping to serum-mcp normalized 0..1" % n[0]
    val, why = _to_target_unit(n[0], n[1], p.get("unit") or "", p.get("min"), p.get("max"), tempo)
    if val is None:
        return why
    bad = _clamp_check(val, p.get("min"), p.get("max"))
    if bad:
        return bad
    t["value"], t["operation"], t["normalized"] = val, "SET", (val != n[0])
    return None


def derive_route(row: Row) -> None:
    from serum_mcp.preset import schema as s
    src, dst = row.context["source"], row.context["destination"]
    m = re.match(r"^(lfo|env|macro)\s*(\d+)$", src.strip().lower())
    source = "%s%d" % (m.group(1), int(m.group(2)) - 1) if m else None
    dests = list(s.MOD_DEST_TARGETS)
    toks = _tokens(dst)
    dest = None
    letter = next((t for t in toks if t in ("a", "b", "c")), None)
    norm = [_SYN.get(t, t) for t in toks if t not in ("a", "b", "c", "filter", "noise", "sub", "main")]
    base = None
    if letter:
        base = "oscillator%d" % (ord(letter) - 97)
    elif "noise" in toks:
        base = "oscillator3"
    elif "filter" in toks:
        n = next((t for t in toks if t.isdigit()), "1")
        base = "filter%d" % (int(n) - 1)
        norm = [t for t in norm if not t.isdigit()]
    if base and norm:
        want = {"freq": "cutoff"}.get(norm[0], norm[0])
        hits = [d for d in dests if d.startswith(base + ".") and d.split(".", 1)[1] == want]
        dest = hits[0] if hits else None
    if source is None or dest is None:
        row.terminal, row.reason = UNSUPPORTED, "route endpoints not expressible: source=%r dest=%r" % (source, dest)
        return
    if row.context.get("transient"):
        row.terminal, row.reason = UNREADABLE, "amount %r came from a transient drag tooltip, not a final static readout" % row.value
        row.read_quality = "TRANSIENT_TOOLTIP_NOT_FINAL"
        row.op = {"kind": "route", "source": source, "destination": dest, "operation": "ADD"}
        return
    if row.value is None:
        row.terminal, row.reason = UNREADABLE, "route amount not read; targeted re-read required"
        row.op = {"kind": "route", "source": source, "destination": dest, "operation": "ADD"}
        return
    n = _numeric(row.value, "%")
    if n is None:
        row.terminal, row.reason = UNSUPPORTED, "amount %r not numeric" % row.value
        return
    row.op = {"kind": "route", "source": source, "destination": dest, "amount": n[0], "operation": "ADD"}
    row.terminal = DERIVED


def tempo_of(rows: List[Row]) -> Optional[float]:
    r = next((r for r in rows if r.control_id == "ableton.tempo"), None)
    n = _numeric(r.value, None) if r else None
    return n[0] if n else None


def build_all(stage_a: Dict[str, Any], reread_log: Optional[Dict[str, Any]] = None) -> List[Row]:
    rows = build_ledger(stage_a) + observed_route_rows(stage_a)
    tempo = tempo_of(rows)
    for r in rows:
        (derive_route(r) if r.control_type == "route" and r.control_id.startswith("route:") else derive(r, tempo))
    for a in (reread_log or {}).get("attempts", []):
        for r in rows:
            if r.control_id == a["target"] and r.terminal == UNREADABLE:
                r.terminal = "UNREADABLE_AFTER_RETRY"
                r.reason = a["reason"]
                r.context["reread"] = {"window_s": a["window_s"], "transients": a.get("observed_transient_values", [])}
    return rows


# --- spec assembly + conservation --------------------------------------------------------

def assemble_spec(rows: List[Row], name: str, description: str, only_admitted: bool = False) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"name": name, "description": description, "oscillators": [], "envelopes": [],
                            "lfos": [], "filters": [], "fx_chain": [], "mod_routes": []}
    fx_order: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for r in sorted((r for r in rows if r.op and (not only_admitted or r.admission == "ADMITTED")), key=lambda r: r.source_ts):
        o = r.op
        if o["kind"] == "route" and r.terminal == DERIVED:
            spec["mod_routes"].append({k: o[k] for k in ("source", "destination", "amount")})
        elif o["kind"] == "field" and r.terminal == DERIVED:
            lst = spec[o["list"]]
            while len(lst) <= o["index"]:
                lst.append({})
            lst[o["index"]][o["field"]] = o["value"]
        elif o["kind"] == "fx":
            key = (r.context.get("rack", 0), o["fx_type"])
            unit = fx_order.setdefault(key, {"type": o["fx_type"], "rack": key[0], "wet": 100, "params": {}})
            if r.terminal == DERIVED:
                if o.get("fidelity") == "APPROXIMATED_FROM_TEMPO" and "kParamBeatSync" in catalog()["fx_params"][o["fx_type"]]:
                    unit["params"]["kParamBeatSync"] = False
                if o["param"] == "kParamWet":
                    unit["wet"] = o["value"]
                else:
                    unit["params"][o["param"]] = o["value"]
    for u in fx_order.values():
        if u["params"].get("kParamBeatSync") is True and any(
                r.op and r.op.get("fidelity") == "APPROXIMATED_FROM_TEMPO" and r.op["fx_type"] == u["type"] for r in rows):
            u["params"]["kParamBeatSync"] = False
    spec["fx_chain"] = list(fx_order.values())
    return {k: v for k, v in spec.items() if v or k in ("name", "description")}


def conservation(stage_a: Dict[str, Any], rows: List[Row]) -> Dict[str, Any]:
    observed = {(c["control_id"], _rack(next((x["value"] for x in fr["controls"] if x["control_id"] == "fx.bus_tabs"), None))
                 if c["control_id"].startswith("fx.") else None)
                for fr in stage_a["frames"] for c in fr["controls"]}
    routes = {(r["source"], r["destination"]) for fr in stage_a["frames"] for r in fr["mod_routes"]}
    ledgered = {(r.control_id, r.context.get("rack")) for r in rows if not r.control_id.startswith("route:")}
    missing = observed - ledgered
    no_terminal = [r.control_id for r in rows if not r.terminal]
    # representable + readable + Atlas-resolved but no operation: implementation gap, not policy.
    gaps = [r.control_id for r in rows if r.terminal in (UNBOUND,) or (r.terminal == UNSUPPORTED and r.op and "blocked" in r.op and "no equivalent" not in r.reason)]
    return {"observed_controls": len(observed), "observed_routes": len(routes), "ledger_rows": len(rows),
            "missing_from_ledger": sorted(map(str, missing)), "rows_without_terminal": no_terminal,
            "terminals": dict(Counter(r.terminal for r in rows)), "compiler_gaps": gaps,
            "invariant_holds": not missing and not no_terminal and len(ledgered) + len(routes) == len(rows)}


def execute_and_verify(rows: List[Row], spec: Dict[str, Any], subfolder: str = "VLP1", only_admitted: bool = False) -> Dict[str, Any]:
    """Write the preset with serum-mcp, read it back, and stamp every derived row with what the
    file actually contains. Nothing is 'executed' until the read-back agrees."""
    from serum_mcp.generation.spec import PresetSpec
    from serum_mcp.tools.generate_preset import generate_preset
    from serum_mcp.preset.packer import unpack_file
    from serum_mcp.preset.introspect import extract_spec
    path = generate_preset(PresetSpec(**spec), subfolder=subfolder).splitlines()[0]
    back = extract_spec(unpack_file(path).data)
    compiled = [r for r in rows if r.op and r.terminal == DERIVED and (not only_admitted or r.admission == "ADMITTED")]

    def close(a, b):
        return math.isclose(float(a), float(b), rel_tol=0.02, abs_tol=1e-3) if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) else a == b
    for r in rows:
        o = r.op
        if not o or r.terminal != DERIVED:
            continue
        if o["kind"] == "field":
            items = getattr(back, o["list"])
            actual = getattr(items[o["index"]], o["field"], None) if o["index"] < len(items) else None
        elif o["kind"] == "fx":
            u = next((u for u in back.fx_chain if u.type == o["fx_type"] and u.rack == r.context.get("rack", 0)), None)
            actual = None if u is None else (u.wet if o["param"] == "kParamWet" else u.params.get(o["param"]))
        else:
            actual = next((m for m in back.mod_routes if m.source == o["source"] and m.destination == o["destination"]), None)
            actual = actual.amount if actual else None
        want = o.get("value", o.get("amount"))
        if r.op.get("fidelity") == "APPROXIMATED_FROM_TEMPO" or (o.get("param") == "kParamBeatSync" and actual is not None and actual != want):
            r.execution = "OVERRIDDEN_APPROXIMATION(observed=%r, file_has=%r)" % (r.value, actual)
        elif not any(x is r for x in compiled):
            r.execution = "NOT_COMPILED"
        elif actual is not None and close(actual, want):
            r.execution = "VERIFIED_EXACT"
        else:
            r.execution = "EXECUTION_MISMATCH(wanted=%r, file_has=%r)" % (want, actual)
    admitted = [r for r in rows if r.admission == "ADMITTED"]
    not_compiled = [r.control_id for r in admitted if r.execution.startswith("NOT_COMPILED")]
    return {"preset_path": path, "execution": dict(Counter(r.execution.split("(")[0] for r in compiled)),
            "admitted": len(admitted), "compiled_admitted": len(admitted) - len(not_compiled),
            "COMPILATION_INCOMPLETE": bool(not_compiled), "admitted_not_compiled": not_compiled}
