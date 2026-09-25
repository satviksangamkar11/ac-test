"""Range Test Plan generation and range characterization (pure; no Serum). Shared by worker.py and the tests.

A control's declared domain is turned into a test vector automatically (no per-parameter code); after the run,
`characterize` separates three things that must never be confused:
  declared   what the schema/Atlas claims
  reachable  what Serum actually retained when written (clamps, drops, default-omission show up here)
  (display)  what the UI shows -- only the GUI layer can fill that, so it is not derived here.

domain = {"kind": "bool|enum|int|continuous|signed|log", "min", "max", "values" (enum), "default" (optional)}
"""
import math


def _uniq(xs):
    out = []
    for x in xs:
        x = float(x)
        if x not in out:
            out.append(x)
    return out


def plan(d: dict) -> dict:
    """-> {"values": [...must be retained...], "probes": [...out-of-range, observation only...]}"""
    k = d["kind"]
    if k == "bool":
        return {"values": [0.0, 1.0], "probes": [2.0]}
    if k == "open":       # no declared bounds anywhere: everything is a probe; the clamp (if any) is discovered from what Serum stores
        m = [1e-3, 1e-2, 0.1, 1.0, 10.0, 100.0, 1e3, 1e4, 1e5, 1e6]
        return {"values": [], "probes": _uniq([x for v in m for x in (v, -v)])}
    if k in ("enum_str", "text"):   # string domains: every vocabulary word must be retained; one invalid word probes what Serum does with it
        return {"values": list(dict.fromkeys(d["values"])), "probes": ["__NOT_A_VALUE__"]}
    if k == "explicit":   # boundary work: caller states exactly which values (retained-required) and probes to write
        return {"values": _uniq(d["values"]), "probes": _uniq(d.get("probes", []))}
    if k == "enum":
        v = sorted(float(x) for x in d["values"])
        return {"values": _uniq(v), "probes": _uniq([v[-1] + 1] + ([v[0] - 1] if v[0] > 0 else []))}
    lo, hi = float(d["min"]), float(d["max"])
    span = hi - lo
    if k == "int":
        pts = [lo, lo + 1, lo + round(span * .25), lo + round(span * .5), lo + round(span * .75), hi - 1, hi]
        return {"values": _uniq(p for p in pts if lo <= p <= hi), "probes": [hi + 1] + ([lo - 1] if lo > 0 else [])}
    if k == "log":
        if lo <= 0:
            raise ValueError("log domain needs min > 0")
        r = hi / lo
        return {"values": _uniq([lo] + [lo * r ** f for f in (.25, .5, .75)] + [hi]),
                "probes": [hi * 1.1, hi * 2, hi * 10, lo / 1.1, lo / 2, lo / 10]}  # escalating: schema bounds are often narrower than Serum's
    if k in ("continuous", "signed"):
        # ponytail: clamp probes to declared bounds to avoid native crashes on out-of-range writes
        # TODO: if Serum rejects in-range writes, escalate probes progressively instead of fixed offsets
        probes_raw = [hi + span * .1, hi + span * .5, hi + span * 2, lo - span * .1, lo - span * .5, lo - span * 2]
        probes = [p for p in probes_raw if lo <= p <= hi]  # clamp; drop any out-of-bounds entirely
        return {"values": _uniq(lo + span * f for f in (0, .25, .5, .75, 1)), "probes": probes if probes else probes_raw[:0]}
    raise ValueError("unknown kind %r" % k)


def close(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return a is not None and a == b
    return a is not None and b is not None and abs(a - b) <= 1e-6 * max(1.0, abs(b))


def characterize(domain: dict, obs: dict) -> dict:
    """obs: {value_key: {"written": v|None, "state_value": s|None, "probe": bool}} -> range fingerprint.

    Serum omits a key whose value equals the true default, so an IN-range value that comes back absent reveals the
    default (`discovered_default`); an out-of-range probe that comes back absent is a clamp onto a default boundary
    when it fits, else a drop."""
    vals = domain.get("values")
    if domain.get("kind") in ("enum_str", "text"):
        return _characterize_str(domain, obs)
    dmin = domain.get("min", min(vals) if vals else None)
    dmax = domain.get("max", max(vals) if vals else None)
    live = [o for o in obs.values() if o["written"] is not None]
    inrange_absent = [o["written"] for o in live if not o.get("probe") and o["state_value"] is None and not o.get("load_error")]
    default = domain.get("default")
    discovered = inrange_absent[0] if inrange_absent else None
    extra_absent = inrange_absent[1:]      # a second, different in-range value that ALSO vanished cannot also be the default
    eff_default = discovered if discovered is not None else default
    rows = []
    for o in live:
        v, s = o["written"], o["state_value"]
        if o.get("load_error"):
            fate = "load_rejected"
        elif close(s, v):
            fate = "retained"
        elif s is None and not o.get("probe") and v in extra_absent:
            fate = "not_retained"
        elif s is None and not o.get("probe"):
            fate = "default_omitted"
        elif s is None:
            if eff_default is not None and dmin is not None and v < dmin and close(eff_default, dmin):
                fate = "clamped_to_min_default_omitted"
            elif eff_default is not None and dmax is not None and v > dmax and close(eff_default, dmax):
                fate = "clamped_to_max_default_omitted"
            else:
                fate = "dropped"
        elif not (isinstance(s, (int, float)) and isinstance(v, (int, float))) or isinstance(s, bool) or isinstance(v, bool):
            fate = "rewritten_type"          # Serum stored a different TYPE than was written (e.g. a sentinel string)
        else:
            fate = "clamped_to_max" if s < v else "clamped_to_min"
        rows.append({"written": v, "stored": s, "fate": fate, "probe": bool(o.get("probe"))})
    kept = [r["stored"] for r in rows if isinstance(r["stored"], (int, float)) and not isinstance(r["stored"], bool)]
    if eff_default is not None and any("default_omitted" in r["fate"] for r in rows):
        kept.append(float(eff_default))
    hi = [r["stored"] if r["stored"] is not None else eff_default for r in rows if r["probe"] and r["fate"].startswith("clamped_to_max")]
    lo = [r["stored"] if r["stored"] is not None else eff_default for r in rows if r["probe"] and r["fate"].startswith("clamped_to_min")]
    rmin, rmax = (min(kept), max(kept)) if kept else (None, None)
    return {"declared": {k: v for k, v in (("kind", domain.get("kind")), ("min", dmin), ("max", dmax), ("default", default)) if v is not None},
            "discovered_default": discovered, "declared_default_matches": None if discovered is None or default is None else close(discovered, default),
            "reachable_min": rmin, "reachable_max": rmax,
            "clamp_high_at": hi[0] if hi else None, "clamp_low_at": lo[0] if lo else None,
            "reaches_beyond_declared_max": bool(kept) and dmax is not None and rmax > dmax * (1 + 1e-6) and not hi,
            "probes_dropped": [r["written"] for r in rows if r["probe"] and r["fate"] == "dropped"],
            "declared_matches_reachable": bool(kept) and dmin is not None and dmax is not None and abs(rmin - dmin) <= 1e-3 * max(1.0, abs(dmin)) and abs(rmax - dmax) <= 1e-3 * max(1.0, abs(dmax)),
            "rows": rows}


def _characterize_str(domain, obs):
    """String domains: which vocabulary words Serum retained, which it omitted (== its default), and what became of the invalid probe."""
    rows, default_word = [], None
    for o in obs.values():
        v, s = o["written"], o["state_value"]
        if v is None:
            continue
        if o.get("load_error"):
            fate = "load_rejected"
        elif close(s, v):
            fate = "retained"
        elif s is None and not o.get("probe") and default_word is not None:
            fate = "not_retained"
        elif s is None and not o.get("probe"):
            fate, default_word = "default_omitted", v
        elif s is None:
            fate = "dropped_or_defaulted"
        else:
            fate = "rewritten"
        rows.append({"written": v, "stored": s, "fate": fate, "probe": bool(o.get("probe"))})
    return {"declared": {"kind": domain["kind"], "values": domain.get("values")}, "discovered_default": default_word, "declared_default_matches": None,
            "reachable_min": None, "reachable_max": None, "clamp_high_at": None, "clamp_low_at": None,
            "vocabulary_retained": [r["written"] for r in rows if not r["probe"] and r["fate"] in ("retained", "default_omitted")],
            "vocabulary_rejected": [r["written"] for r in rows if not r["probe"] and r["fate"] not in ("retained", "default_omitted")],
            "probes_dropped": [r["written"] for r in rows if r["probe"] and r["fate"] != "retained"],
            "declared_matches_reachable": all(r["fate"] in ("retained", "default_omitted") for r in rows if not r["probe"]), "rows": rows}
