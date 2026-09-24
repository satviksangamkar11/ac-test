"""State ledger: every control Stage-A observed gets exactly one terminal outcome.

Observation must never disappear. It may become IGNORED / UNREADABLE / UNRESOLVED / UNBOUND / UNSUPPORTED /
OPERATION_DERIVED -- never nothing. Nothing is keyed to a specific video and nothing is inferred:

  * identity comes from the Atlas only;
  * the Atlas id -> serum-mcp target mapping comes ONLY from the committed, reviewable
    serum2/reference/serum_mcp_binding_table.json (exact-normalised or reviewed-alias entries); an id with no
    entry is UNBOUND -- there is no fuzzy, prefix, synonym or "some sibling field accepts this value" fallback;
  * an unreadable observation is never replaced by an earlier reading, a default, or memory;
  * this module can only DERIVE operations. It cannot compile or execute anything: the executable object is an
    AuthorizedOperation (serum2/execution/authorized_state_compiler.py), which exists only after admission.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "serum-mcp" / "src"))
from serum2.reference.serum_atlas import normalize_control, get_control, all_control_ids, EXACT, ALIAS  # noqa: E402

UNREADABLE_FINAL = "UNREADABLE_AFTER_RETRY"
IGNORED_NAVIGATION = "IGNORED_NAVIGATION"
NOT_SERUM_SURFACE = "NOT_SERUM_SURFACE"
UNREADABLE = "UNREADABLE_RE_READ_REQUIRED"
UNRESOLVED = "REFUSED_UNRESOLVED_REFERENCE"
UNBOUND = "UNBOUND_TO_SERUM_PARAM"
UNSUPPORTED = "UNSUPPORTED_VALUE"
DERIVED = "OPERATION_DERIVED"
NAV_TYPES = {"tab", "badge_count"}
TABLE_PATH = Path(__file__).resolve().parents[1] / "reference" / "serum_mcp_binding_table.json"


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


# --- observation -> rows --------------------------------------------------------------------------------

def _rack(bus: Optional[str]) -> int:
    m = re.search(r"(\d)", bus or "")
    return int(m.group(1)) if m else 0


def build_ledger(stage_a: Dict[str, Any], corrections: Optional[Dict[str, Any]] = None) -> List[Row]:
    """One row per (control_id, fx rack) from the FULL observation set, not from diffs. The row carries the LAST
    reading; if that reading is unreadable the row is unreadable (an earlier value is recorded, never used).
    `corrections` is an explicit audited id overlay (values are never edited); each applied one is recorded."""
    fix = {c["from"]: c for c in (corrections or {}).get("corrections", [])}
    rows: Dict[Tuple[str, Any], Row] = {}
    for fr in stage_a["frames"]:
        bus = next((c["value"] for c in fr["controls"] if c["control_id"] == "fx.bus_tabs"), None)
        for c in fr["controls"]:
            applied = fix.get(c["control_id"])
            c = {**c, "control_id": applied["to"]} if applied else c
            rack = _rack(bus) if c["control_id"].startswith("fx.") else None
            key = (c["control_id"], rack)
            prev = rows.get(key)
            row = Row(c["control_id"], c["value"], c.get("unit"), c["status"], c["control_type"],
                      fr["timestamp_sec"], (prev.n_readings + 1) if prev else 1,
                      bool(prev and (prev.value != c["value"] or prev.changed_from_previous)),
                      {"rack": rack} if rack is not None else {})
            if applied:
                row.context["stage_a_correction"] = {"from": applied["from"], "to": applied["to"], "reason": applied["reason"]}
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


def observed_route_rows(stage_a: Dict[str, Any]) -> List[Row]:
    """One row per (source, destination). The row is the LAST observation of that route, exactly as read: an amount
    that is unreadable in the last observation stays unreadable -- earlier amounts are never carried forward."""
    routes: Dict[Tuple[str, str], Row] = {}
    for fr in stage_a["frames"]:
        for r in fr["mod_routes"]:
            k = (r["source"], r["destination"])
            n = (routes[k].n_readings + 1) if k in routes else 1
            routes[k] = Row("route:%s->%s" % k, r["amount"], None, r["status"], "route", fr["timestamp_sec"], n, False,
                            {"source": r["source"], "destination": r["destination"], "bipolar": r.get("bipolar"),
                             "transient": "tooltip" in (r.get("note") or "").lower()})
    return list(routes.values())


# --- serum-mcp catalog + the explicit binding table --------------------------------------------------------

_CATALOG: Dict[str, Any] = {}
_TABLE: Dict[str, Any] = {}


def catalog() -> Dict[str, Any]:
    if not _CATALOG:
        from serum_mcp.tools.list_parameters import list_parameters
        r = list_parameters()
        _CATALOG.update(json.loads(r) if isinstance(r, str) else r)
    return _CATALOG


def binding_table() -> Dict[str, Any]:
    if not _TABLE:
        _TABLE.update(json.loads(TABLE_PATH.read_text(encoding="utf-8")))
    return _TABLE


def exact_norm(s: Any) -> str:
    s = str(s)
    if re.match(r"^k[A-Z]", s):
        s = s[1:]
    return re.sub(r"[^a-z0-9]", "", s.lower())


def resolve_enum(control_id: str, observed: str, domain: List[str]) -> Tuple[Optional[str], bool, str]:
    """observed UI label -> serum-mcp value. Approved alias (with cited evidence) first, then EXACT normalised
    equality against the serum-mcp domain (unique). Nothing else. Returns (value, normalized, why-not)."""
    alias = binding_table()["value_aliases"].get(control_id, {}).get(observed)
    if alias:
        return (alias["value"], True, "") if alias["value"] in domain else (None, False, "approved alias %r not in serum-mcp domain" % alias["value"])
    hits = [d for d in domain if exact_norm(d) == exact_norm(observed)]
    if len(hits) == 1:
        return hits[0], hits[0] != observed, ""
    return None, False, "no approved mapping of %r into the serum-mcp vocabulary" % observed


# --- value coercion (unit handling only; no guessing) -----------------------------------------------------

_NUM = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(ms|s|hz|khz|db|%|:1)?\s*$", re.I)
_UNIT_ALIAS = {"s": "seconds", "sec": "seconds", ":1": "ratio:1"}
_NOTE = re.compile(r"^\s*(\d+)/(\d+)\s*$")


def _numeric(value: Any, unit: Optional[str]) -> Optional[Tuple[float, str]]:
    m = _NUM.match(str(value))
    return (float(m.group(1)), (m.group(2) or (unit or "")).lower()) if m else None


def _display_curve(fi) -> Optional[Dict[str, Any]]:
    extra = getattr(fi, "json_schema_extra", None)
    return extra.get("display_curve") if isinstance(extra, dict) else None


def _display_exponent(curve) -> Optional[float]:
    """display_fraction = raw ** exponent. Returns the exponent, or None when the curve is undeclared/invalid."""
    if isinstance(curve, dict) and curve.get("kind") == "power":
        n = curve.get("exponent")
        if isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0:
            return float(n)
    return None


def _to_target_unit(num: float, unit: str, target_unit: str, lo, hi,
                    curve: Optional[Dict[str, Any]] = None) -> Tuple[Optional[float], str]:
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
    if unit == "db" and (lo, hi) == (0.0, 1.0) and tu in ("", "normalized", "linear"):
        return None, "dB -> normalized 0..1 has no calibrated mapping"
    if unit == "%" and hi is not None and hi <= 1.0:
        n = _display_exponent(curve)
        if n is None:
            return None, "%% -> normalized 0..1 has no declared display_curve (got %r)" % (curve,)
        return (num / 100.0) ** (1.0 / n), ""
    if unit == "%" and tu in ("%", "percent", ""):
        return num, ""
    return None, "no conversion %s -> %s" % (unit, target_unit or "unitless")


def _clamp_check(v: float, lo, hi) -> Optional[str]:
    if lo is not None and v < lo:
        return "value %s below serum-mcp minimum %s" % (v, lo)
    if hi is not None and v > hi:
        return "value %s above serum-mcp maximum %s" % (v, hi)
    return None


def _field_range(fi):
    lo = hi = None
    for m in fi.metadata:
        lo, hi = getattr(m, "ge", lo), getattr(m, "le", hi)
    return lo, hi


def _domain(fieldname: str, module: str, desc: str) -> Optional[List[str]]:
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
    m = re.search(r"one of:? ([^.]+)", desc or "")
    return [x.strip(" '\"") for x in m.group(1).split(",")] if m else None


# --- derive -------------------------------------------------------------------------------------------------

def derive(row: Row, tempo: Optional[float]) -> None:
    cid = row.control_id
    if row.control_type in NAV_TYPES:
        row.terminal, row.reason = IGNORED_NAVIGATION, "control_type=%s (UI navigation)" % row.control_type
        return
    res = normalize_control(cid)
    if res.status not in (EXACT, ALIAS):
        top = cid.split(".")[0]
        known = {i.split(".")[0] for i in all_control_ids()}
        if top not in known:
            row.terminal, row.reason = NOT_SERUM_SURFACE, "namespace %r not a Serum module in Atlas" % top
        else:
            row.terminal, row.reason = UNRESOLVED, "Atlas status=%s" % res.status
        return
    if row.value is None or str(row.value).strip() in ("", "-") or row.status != "OBSERVED":
        row.terminal, row.reason = UNREADABLE, "value=%r status=%s; targeted re-read required" % (row.value, row.status)
        return
    entry = binding_table()["controls"].get(res.canonical_id)
    if entry is None:
        row.terminal, row.reason = UNBOUND, "no approved entry for %s in serum_mcp_binding_table.json" % res.canonical_id
        return
    target = {k: v for k, v in entry.items() if k != "basis"}
    target["binding_basis"] = entry["basis"]
    row.op = target
    err = _coerce(row, target, res.canonical_id, tempo)
    if err:
        row.terminal, row.reason, row.op = UNSUPPORTED, err, {**target, "blocked": err}
    else:
        row.terminal = DERIVED


def _coerce(row: Row, t: Dict[str, Any], canon: str, tempo: Optional[float]) -> Optional[str]:
    from serum_mcp.generation import spec as S
    models = {"osc": S.OscillatorSpec, "env": S.EnvelopeSpec, "lfo": S.LfoSpec, "filter": S.FilterSpec}
    v = str(row.value).strip()
    if t["kind"] == "field":
        fi = models[t["module"]].model_fields[t["field"]]
        ann = str(fi.annotation)
        if "bool" in ann:
            if v.lower() in ("on", "true"):
                t["value"] = True
            elif v.lower() in ("off", "false"):
                t["value"] = False
            else:
                return "non-boolean %r for boolean field" % v
            t["operation"] = "TOGGLE_ON" if t["value"] else "TOGGLE_OFF"
            return None
        dom = _domain(t["field"], t["module"], fi.description)
        if dom and "str" in ann:
            hit, norm_flag, why = resolve_enum(canon, v, dom)
            if hit is None:
                return why
            t["value"], t["operation"], t["normalized"] = hit, "SELECT", norm_flag
            return None
        n = _numeric(v, row.unit)
        if n is None:
            return "value %r is not numeric for field %s" % (v, t["field"])
        lo, hi = _field_range(fi)
        val, why = _to_target_unit(n[0], n[1], "seconds" if "seconds" in (fi.description or "").lower() else "", lo, hi,
                                   _display_curve(fi))
        if val is None:
            return why
        bad = _clamp_check(val, lo, hi)
        if bad:
            return bad
        t["value"], t["operation"], t["normalized"] = val, "SET", (val != n[0])
        return None
    p = catalog()["fx_params"][t["fx_type"]].get(t["param"])
    if p is None:
        return "binding table names %s.%s which is not in the serum-mcp catalog" % (t["fx_type"], t["param"])
    if p["kind"] == "enum":
        hit, norm_flag, why = resolve_enum(canon, v, p["enum_values"])
        if hit is None:
            return why
        t["value"], t["operation"], t["normalized"] = hit, "SELECT", norm_flag
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
    if p.get("unit") == "normalized" and (n[1] != "" or (p.get("max") == 1.0 and n[0] > 1.0)):
        return "%s value has no calibrated mapping to serum-mcp normalized 0..1" % (n[1] or "raw")
    val, why = _to_target_unit(n[0], n[1], p.get("unit") or "", p.get("min"), p.get("max"))
    if val is None:
        return why
    bad = _clamp_check(val, p.get("min"), p.get("max"))
    if bad:
        return bad
    t["value"], t["operation"], t["normalized"] = val, "SET", (val != n[0])
    return None


def derive_route(row: Row) -> None:
    src, dst = row.context["source"], row.context["destination"]
    m = re.match(r"^(lfo|env|macro)\s*(\d+)$", src.strip().lower())
    source = "%s%d" % (m.group(1), int(m.group(2)) - 1) if m else None
    dest = binding_table()["route_destinations"].get(dst.strip())
    if source is None or dest is None:
        row.terminal, row.reason = UNSUPPORTED, "route endpoints have no approved mapping: source=%r dest=%r" % (source, dest)
        return
    op = {"kind": "route", "source": source, "destination": dest, "operation": "ADD"}
    if row.context.get("transient"):
        row.terminal, row.reason, row.read_quality, row.op = UNREADABLE, (
            "amount %r came from a transient drag tooltip, not a final static readout" % row.value), "TRANSIENT_TOOLTIP_NOT_FINAL", op
        return
    if row.value is None:
        row.terminal, row.reason, row.op = UNREADABLE, "route amount not read; targeted re-read required", op
        return
    n = _numeric(row.value, "%")
    if n is None:
        row.terminal, row.reason = UNSUPPORTED, "amount %r not numeric" % row.value
        return
    row.op = {**op, "amount": n[0]}
    row.terminal = DERIVED


def tempo_of(rows: List[Row]) -> Optional[float]:
    r = next((r for r in rows if r.control_id == "ableton.tempo"), None)
    n = _numeric(r.value, None) if r else None
    return n[0] if n else None


def build_all(stage_a: Dict[str, Any], reread_log: Optional[Dict[str, Any]] = None,
              corrections: Optional[Dict[str, Any]] = None) -> List[Row]:
    rows = build_ledger(stage_a, corrections) + observed_route_rows(stage_a)
    tempo = tempo_of(rows)
    for r in rows:
        (derive_route(r) if r.control_type == "route" and r.control_id.startswith("route:") else derive(r, tempo))
    for a in (reread_log or {}).get("attempts", []):
        for r in rows:
            if r.control_id == a["target"] and r.terminal == UNREADABLE:
                r.terminal = UNREADABLE_FINAL
                r.reason = a["reason"]
                r.context["reread"] = {"window_s": a["window_s"], "transients": a.get("observed_transient_values", [])}
    return rows


def conservation(stage_a: Dict[str, Any], rows: List[Row], corrections: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fix = {c["from"]: c["to"] for c in (corrections or {}).get("corrections", [])}
    observed = {(fix.get(c["control_id"], c["control_id"]),
                 _rack(next((x["value"] for x in fr["controls"] if x["control_id"] == "fx.bus_tabs"), None))
                 if fix.get(c["control_id"], c["control_id"]).startswith("fx.") else None)
                for fr in stage_a["frames"] for c in fr["controls"]}
    routes = {(r["source"], r["destination"]) for fr in stage_a["frames"] for r in fr["mod_routes"]}
    ledgered = {(r.control_id, r.context.get("rack")) for r in rows if not r.control_id.startswith("route:")}
    missing = observed - ledgered
    no_terminal = [r.control_id for r in rows if not r.terminal]
    return {"observed_controls": len(observed), "observed_routes": len(routes), "ledger_rows": len(rows),
            "missing_from_ledger": sorted(map(str, missing)), "rows_without_terminal": no_terminal,
            "terminals": dict(Counter(r.terminal for r in rows)),
            "invariant_holds": not missing and not no_terminal and len(ledgered) + len(routes) == len(rows)}
