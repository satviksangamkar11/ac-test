"""Phase F: ProductionEvent -> ProducerRequest candidates.

The bridge that makes "the Brain reasons over the complete event, not a
preselected knob" real: every observed change in a ProductionEvent becomes
its own ProducerRequest candidate, each independently resolved/admitted
through the existing, unmodified authority chain. This module NEVER
decides what's executable -- it only proposes candidates; Resolution and
Admission (unchanged) decide which ones actually go anywhere.

Reuses existing vocabulary rather than inventing a parallel one:
  - scalar control changes -> visual_reasoner's _TARGET_TO_CONCEPT /
    _TARGET_DIRECTION_WORDS (the same tables the k6/Env1.Release episodes
    already used) map a control_id to a concept-based user_intent string.
  - route changes -> ADD_MODULATION_ROUTE structured operation (the same
    shape producer_brain.py's _run_modulation_route_operation expects).

A control_id with no matching entry in either vocabulary produces no
candidate -- honest omission, never a guessed concept.
"""
from __future__ import annotations

from typing import Any, Dict, List

from serum2.source.visual_evidence import ProductionEvent


def _control_id_to_target_name(control_id: str) -> str:
    """'env1.release' -> 'Env1.Release', 'filter1.cutoff' -> 'Filter1.Cutoff'.
    Matches the capitalization convention visual_reasoner's lookup tables
    use, without hardcoding a second copy of those tables."""
    parts = control_id.split(".")
    return ".".join(p[:1].upper() + p[1:] for p in parts if p)


def production_event_to_requests(event: ProductionEvent) -> List[Dict[str, Any]]:
    """Returns a list of {"request_kwargs": {...}, "source_control_id": str|None}
    dicts. `request_kwargs` are passed straight to ProducerRequest(**kwargs)
    by the caller (only real ProducerRequest fields -- kept separate from
    `source_control_id` so callers never accidentally pass an unknown kwarg
    into the dataclass constructor). Avoids a circular import with
    producer_brain.py, which may itself import this module later.

    One candidate per observed change, independent of which change the
    transcript happened to name -- CONFLICT/VISUAL_ONLY/AGREEMENT events all
    produce candidates the same way; fusion_status is metadata for the
    episode record, not a filter on which candidates get proposed.
    """
    from serum2.producer.visual_reasoner import _TARGET_TO_CONCEPT, _TARGET_DIRECTION_WORDS, _numeric_with_unit

    diff = event.snapshot_diff or {}
    candidates: List[Dict[str, Any]] = []

    for c in diff.get("changed_controls", []):
        target_name = _control_id_to_target_name(c["control_id"])
        concept = _TARGET_TO_CONCEPT.get(target_name)
        if concept is None:
            continue  # no known vocabulary for this control -- honest omission
        before_num = _numeric_with_unit(str(c["before"]))
        after_num = _numeric_with_unit(str(c["after"]))
        inc_word, dec_word = _TARGET_DIRECTION_WORDS.get(target_name, ("higher", "lower"))
        direction = None
        if before_num and after_num and before_num[1] == after_num[1]:
            direction = inc_word if after_num[0] > before_num[0] else dec_word
        if direction is None:
            continue  # direction not determinable from these two readings

        candidates.append({
            "request_kwargs": {
                "user_intent": "%s %s to %s" % (direction, target_name, c["after"]),
                "mode": "EXECUTE", "visual_mode": "NEVER",
            },
            "source_control_id": c["control_id"],
        })

    for r in diff.get("added_routes", []):
        candidates.append({
            "request_kwargs": {
                "user_intent": "",
                "operation": "ADD_MODULATION_ROUTE",
                "operation_args": {
                    "source": r.get("source"), "destination": r.get("destination"),
                    "amount": r.get("amount"), "bipolar": r.get("bipolar"),
                },
                "mode": "EXECUTE",
            },
            "source_control_id": None,
        })

    return candidates
