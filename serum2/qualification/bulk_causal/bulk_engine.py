"""TRUE context-based bulk verification engine (pure: no Serum, no old-repo imports; the Serum side is a Backend).

One CONTEXT = one canonical base state, loaded once per Serum session. Many PARAMETERS are then swept inside it:

    context base body  --(deepcopy, RAW mutation of one path)-->  transport state  -->  Backend.load  -->  observe
                                   ^                                                                        |
                                   +---------------- Backend.load(base) + verify restoration  <-------------+

No .SerumPreset is written per parameter/value. The only persistent artifact is the context's own preset (written by the
caller, once); Backend.load may use ONE reused transient transport file. The engine itself never touches disk.

Backend protocol (implemented by serum_backend.SerumBackend and by test fakes):
    load(body: dict)  -> None   put this full preset body into the live instance
    observe()         -> {"state": body-as-Serum-re-saved-it, "band_db": [...], "hosts": {name: display text}}
"""
import copy
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from range_plan import characterize, close, plan as range_plan  # noqa: E402


# ---------------------------------------------------------------- raw mutation (generic over families) -------------
def resolve_path(m: dict) -> list:
    """A mutation is either {"kind":"raw_path","path":[...]} (any family) or the FX convenience form
    {"kind":"fx_param","index":i,"module":<FX type>,"kparam":<raw key>,"rack":0}."""
    if m["kind"] == "raw_path":
        return list(m["path"])
    if m["kind"] == "fx_param":
        return ["FXRack%d" % m.get("rack", 0), "FX", m.get("index", 0), m["module"], "plainParams", m["kparam"]]
    raise ValueError("unknown mutation kind %r" % m["kind"])


def body_get(body, path, default=None):
    cur = body
    for p in path:
        try:
            cur = cur[p]
        except (KeyError, IndexError, TypeError):
            return default
    return cur


def body_set(body, path, value):
    """Set a raw value, creating the container dict when Serum's untouched sentinel string ('default') sits there."""
    cur = body
    for i, p in enumerate(path[:-1]):
        nxt = cur[p]
        if isinstance(nxt, str):  # e.g. plainParams == 'default'
            nxt = cur[p] = {}
        cur = nxt
    cur[path[-1]] = value


def body_delete(body, path):
    parent = body_get(body, path[:-1])
    if isinstance(parent, dict):
        parent.pop(path[-1], None)


def roundtrip_ok(meta, body, path, v) -> bool:
    """In-memory .SerumPreset container round trip (pack -> unpack): the raw key must survive with the written value."""
    from preset_build import pack_unpack
    back = body_get(pack_unpack(meta, body), path)
    return close(back, v) if isinstance(v, (int, float)) else back == v


def sha(body) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=repr).encode()).hexdigest()[:16]


def diff_keys(a, b) -> list:
    """Keys whose value differs between two plainParams-like dicts (sentinel strings count as empty)."""
    a, b = (a if isinstance(a, dict) else {}), (b if isinstance(b, dict) else {})
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


# ---------------------------------------------------------------- the engine -------------------------------------------
def run_parameter(base_body, base_obs, floor, param, backend, cfg, counters, meta=None):
    path = resolve_path(param["mutation"])
    kp = path[-1]
    domain = param["domain"]
    vec = range_plan(domain)
    values = [(v, False) for v in vec["values"]] + [(v, True) for v in vec["probes"]]
    container = path[:-1]
    rows, obs = [], {}
    for v, probe in values:
        body = copy.deepcopy(base_body)          # isolation: every mutation starts from the pristine context body
        body_set(body, path, v)
        backend.load(body)
        counters["state_loads"] += 1
        o = backend.observe()
        sv = body_get(o["state"], path)
        rows.append({"written": v, "probe": probe, "state_value": sv,
                     "state_diff_keys": diff_keys(body_get(base_obs["state"], container), body_get(o["state"], container)),
                     "file_roundtrip": None if meta is None else roundtrip_ok(meta, body, path, v), "band_db": o["band_db"], "band_delta_db": [round(a - b, 2) for a, b in zip(o["band_db"], base_obs["band_db"])],
                     "host_params_changed": sorted(k for k in o["hosts"] if o["hosts"][k] != base_obs["hosts"].get(k))[:8]})
        obs[repr(v)] = {"written": v, "state_value": sv, "probe": probe}
    backend.load(base_body)                       # restore the context baseline ...
    counters["state_loads"] += 1
    counters["baseline_reloads"] = counters.get("baseline_reloads", 0) + 1
    after = backend.observe()
    drift = max(abs(a - b) for a, b in zip(after["band_db"], base_obs["band_db"]))
    same_state = body_get(after["state"], container) == body_get(base_obs["state"], container)  # ... and verify it
    return {"atlas_id": param.get("atlas_id"), "context": param["context"], "candidate": {"kind": param["mutation"]["kind"], "path": path, "kparam": kp},
            "declared": domain, "value_vector": vec, "values": rows, "range": characterize(domain, obs),
            "restoration": {"ok": bool(same_state and drift <= floor), "band_drift_db": round(drift, 2), "container_state_identical": bool(same_state)},
            "noise_floor_db": floor}


def run_context(name, base_body, params, backend_factory, cfg, counters=None, meta=None):
    """Sweep `params` (all belonging to context `name`) against base_body. A fresh backend (Serum instance) is built every
    cfg['session_size'] parameters and the context base is loaded once into each; returns the per-parameter evidence."""
    counters = counters if counters is not None else {}
    counters.setdefault("state_loads", 0)
    counters.setdefault("sessions", 0)
    size = cfg.get("session_size", 10)
    pristine = sha(base_body)
    records, backend, base_obs, floor = [], None, None, None
    for i, p in enumerate(params):
        if backend is None or i % size == 0:
            backend = backend_factory()
            counters["sessions"] += 1
            backend.load(base_body)               # the context is loaded ONCE per session batch
            counters["context_loads"] = counters.get("context_loads", 0) + 1
            counters["state_loads"] += 1
            base_obs = backend.observe()
            backend.load(base_body)               # a second baseline load only to measure the noise floor
            counters["baseline_reloads"] = counters.get("baseline_reloads", 0) + 1
            counters["state_loads"] += 1
            again = backend.observe()
            floor = max(cfg.get("min_noise_floor_db", 0.5), 2 * max(abs(a - b) for a, b in zip(base_obs["band_db"], again["band_db"])))
        records.append(run_parameter(base_body, base_obs, floor, p, backend, cfg, counters, meta))
    assert sha(base_body) == pristine, "the context body must never be mutated in place"
    return records
