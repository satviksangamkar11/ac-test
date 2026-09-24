"""Agreement between the new context-bulk evidence and the legacy per-test range evidence (pure).

    python compare.py <bulk_evidence.json> <legacy_range_evidence.json>

Compares, per shared kparam: the value vector, each value's retained state value, and the range fingerprint. The legacy harness
generated one preset per value; the bulk engine must reach the same conclusions from one context.
"""
import json
import sys

FIELDS = ("declared", "discovered_default", "reachable_min", "reachable_max", "clamp_high_at", "clamp_low_at", "probes_dropped")


def close(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= 1e-6 * max(1.0, abs(b)))


def same(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return close(a, b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) or a is None or b is None else a == b


def compare(bulk, legacy):
    old = {r["candidate"]["kparam"]: r for r in legacy["records"]}
    out = {}
    for r in bulk["records"]:
        kp = r["candidate"]["kparam"]
        if kp not in old:
            continue
        o = old[kp]
        bv = {repr(v["written"]): v["state_value"] for v in r["values"]}
        ov = {k: x["state_value"] for k, x in o["observations"].items() if x["written"] is not None}
        diffs = [f for f in FIELDS if not same(r["range"].get(f), o["range"].get(f))]
        if not same(bv, ov):
            diffs.append("per_value_state")
        out[kp] = {"agree": not diffs, "differs_in": diffs}
    return out


if __name__ == "__main__":
    res = compare(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
    for k, v in res.items():
        print(k, "AGREE" if v["agree"] else "DIFFERS %s" % v["differs_in"])
