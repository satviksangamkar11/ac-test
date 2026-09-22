"""U8: account for every observed change in a timeline with an explicit terminal layer.

No new authority: candidates come from production_event_to_requests, refusals are mapped through
target_resolution's existing taxonomy, and admission stays with ProducerBrain. Changes the event
bridge cannot turn into a request are NOT dropped -- they terminate at REFERENCE or OPERATION.
"""
from __future__ import annotations

from typing import Any, Dict, List

from serum2.producer.event_to_intent import production_event_to_requests
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
from serum2.producer.target_resolution import (
    LAYER_BRAIN, LEGACY_STATUS_TO_REFUSAL, REFUSED_AMBIGUOUS_REFERENCE, REFUSED_NO_BRAIN_CONCEPT,
    REFUSED_UNRESOLVED_REFERENCE,
)
from serum2.reference.serum_atlas import EXACT, ALIAS, AMBIGUOUS, normalize_control

ADMITTED = "ADMITTED_EXECUTABLE"
NO_OPERATION = "NO_OPERATION_DERIVED"   # identified control, but before/after is not an increase/decrease


def _row(event, kind, ident, terminal, layer, **kw) -> Dict[str, Any]:
    return {"event_id": event.event_id, "window": [event.start_timestamp_sec, event.end_timestamp_sec],
            "fusion": event.fusion_status, "kind": kind, "id": ident, "terminal": terminal, "layer": layer, **kw}


def audit_events(events, brain: ProducerBrain = None) -> List[Dict[str, Any]]:
    brain = brain or ProducerBrain()
    rows: List[Dict[str, Any]] = []
    for e in events:
        diff = e.snapshot_diff or {}
        by_control = {}
        for c in production_event_to_requests(e):
            if c["source_control_id"]:
                by_control[c["source_control_id"]] = c
            else:  # route candidate
                r = brain.execute(ProducerRequest(**c["request_kwargs"]))
                a = c["request_kwargs"]["operation_args"]
                rows.append(_row(e, "route", "%s->%s" % (a["source"], a["destination"]), *_terminal(r), status=r.execution_status))
        for ch in diff.get("changed_controls", []):
            cid = ch["control_id"]
            obs = {"before": ch["before"], "after": ch["after"]}
            res = normalize_control(cid)
            if res.status == AMBIGUOUS:
                rows.append(_row(e, "control", cid, REFUSED_AMBIGUOUS_REFERENCE, "REFERENCE_RESOLUTION", **obs))
            elif res.status not in (EXACT, ALIAS):
                rows.append(_row(e, "control", cid, REFUSED_UNRESOLVED_REFERENCE, "REFERENCE_RESOLUTION", **obs))
            elif cid in by_control:
                r = brain.execute(ProducerRequest(**by_control[cid]["request_kwargs"]))
                # Atlas already identified it, so the Brain's unknown-concept refusal is a vocabulary gap, not a reference failure.
                term = (REFUSED_NO_BRAIN_CONCEPT, LAYER_BRAIN) if r.execution_status == "REFUSED_UNKNOWN_CONCEPT" else _terminal(r)
                rows.append(_row(e, "control", cid, *term, status=r.execution_status, route=r.execution_route,
                                 concept=r.resolved_concept, **obs))
            else:
                rows.append(_row(e, "control", cid, NO_OPERATION, "OPERATION", canonical=res.canonical_id, **obs))
        for r_ in diff.get("newly_observed_routes", []):
            rows.append(_row(e, "route", "%s->%s" % (r_.get("source"), r_.get("destination")),
                             "NEWLY_OBSERVED_ROUTE_NO_BASELINE", "OBSERVATION", amount=r_.get("amount")))
    return rows


def _terminal(r):
    if r.admitted:
        return ADMITTED, "AUTHORIZED_EXECUTION"
    code, layer = LEGACY_STATUS_TO_REFUSAL.get(r.execution_status or "", (None, None))
    return code or r.execution_status or "REFUSED_UNCLASSIFIED", layer or "UNKNOWN"
