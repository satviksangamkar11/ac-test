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
        return {"values": _uniq(lo + span * f for f in (0, .25, .5, .75, 1)),
                "probes": [hi + span * .1, hi + span * .5, hi + span * 2, lo - span * .1, lo - span * .5, lo - span * 2]}
    raise ValueError("unknown kind %r" % k)


def close(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-6 * max(1.0, abs(b))


def characterize(domain: dict, obs: dict) -> dict:
    """obs: {value_key: {"written": v|None, "state_value": s|None, "probe": bool}} -> range fingerprint.

    Serum omits a key whose value equals the true default, so an IN-range value that comes back absent reveals the
    default (`discovered_default`); an out-of-range probe that comes back absent is a clamp onto a default boundary
    when it fits, else a drop."""
    vals = domain.get("values")
    dmin = domain.get("min", min(vals) if vals else None)
    dmax = domain.get("max", max(vals) if vals else None)
    live = [o for o in obs.values() if o["written"] is not None]
    inrange_absent = [o["written"] for o in live if not o.get("probe") and o["state_value"] is None]
    default = domain.get("default")
    discovered = inrange_absent[0] if inrange_absent else None
    eff_default = discovered if discovered is not None else default
    rows = []
    for o in live:
        v, s = o["written"], o["state_value"]
        if close(s, v):
            fate = "retained"
        elif s is None and not o.get("probe"):
            fate = "default_omitted"
        elif s is None:
            if eff_default is not None and dmin is not None and v < dmin and close(eff_default, dmin):
                fate = "clamped_to_min_default_omitted"
            elif eff_default is not None and dmax is not None and v > dmax and close(eff_default, dmax):
                fate = "clamped_to_max_default_omitted"
            else:
                fate = "dropped"
        else:
            fate = "clamped_to_max" if s < v else "clamped_to_min"
        rows.append({"written": v, "stored": s, "fate": fate, "probe": bool(o.get("probe"))})
    kept = [r["stored"] for r in rows if r["stored"] is not None]
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
