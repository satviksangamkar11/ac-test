"""Wires the Producer Brain into the reference-reproduction path for real, per
REFERENCE_REPRODUCTION_PLAYBOOK.md section 0/14: "Brain receives complete reference knowledge... Brain can retrieve,
explain, correlate, summarize, reason, identify missing information... Brain cannot authorize, mutate Serum,
fabricate evidence, invent missing values, bypass contracts, bypass admission."

Neither existing path did this before: `orchestrator.py` called the Brain's CREATE-mode `execute_producer_request`
and threw the answer away; `run_reference_reproduction` doesn't consult the Brain at all (Stage-A -> ledger ->
admission directly). This module is the missing, narrow piece: it calls ONLY `ProducerBrain._retrieve_knowledge`
-- the same method the module's own docstring already documents as "advisory only... never CapabilityResolver or
admission" -- once per ledger row, over the COMPLETE ledger (every terminal disposition, not only DERIVED rows).
It never constructs a ProducerRequest, never calls `.execute()`, `admit_rows()`, or any compiler/comparator
function. There is no code path here that can change which operations get admitted or compiled.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from serum2.producer.producer_brain import ProducerBrain


def brief_row(brain: ProducerBrain, row: Dict[str, Any]) -> Dict[str, Any]:
    """One ledger row -> one advisory brief entry. `row` is whatever `state_ledger.build_all` produced for one
    control: at minimum a target/control id and a `terminal` disposition. Retrieval is free-text over the raw
    target id -- no concept-vocabulary guess is made, so a target with no corpus coverage legitimately returns
    zero knowledge items rather than a fabricated one."""
    target = row.get("control_id") or row.get("atlas_id") or row.get("target") or "<unknown>"
    contributions, notes = brain._retrieve_knowledge(intent_text=target, concept=None)
    return {
        "target": target, "terminal": row.get("terminal"), "reason": row.get("reason"),
        "brain_knowledge_item_count": len(contributions),
        "brain_notes": notes,
    }


def brief_reference_knowledge(rows: List[Dict[str, Any]], brain: Optional[ProducerBrain] = None) -> List[Dict[str, Any]]:
    """The complete Reference Knowledge briefing: one entry per ledger row, in the same order, none dropped.
    Purely additive annotation for the forensic report -- callers must not use this list's contents to decide
    admission, compilation, or which operations execute; that decision is already made by `admit_rows`/
    `compile_ops` before or independently of this call."""
    brain = brain or ProducerBrain()
    return [brief_row(brain, row) for row in rows]
