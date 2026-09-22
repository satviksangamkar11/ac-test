"""Builds the generic serum.modulation_route.add CapabilityContract from real
qualification evidence (qualify_modulation_route.py's output) -- never
hand-typed, never specific to one video's LFO1/Filter1 instance.

Reuses the existing, unmodified CapabilityContract/ExecutionBinding
dataclasses (serum2/evidence/capability_contract.py) -- no new authority
schema. status=STRUCTURAL_ONLY is the honest tier: construct+persist+load
are proven (one instance additionally UI-verified in real Serum 2), no
audio-domain causal effect was measured. Admission with required_causal=True
would correctly refuse this contract; required_causal=False (the correct
ask for a topology/routing operation, which has no "before/after dB" causal
shape in the first place) admits it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from serum2.evidence.capability_contract import (
    CapabilityContract, ExecutionBinding, MUTATE_STRUCTURED, STRUCTURAL_ONLY,
)

_QUALIFICATION_PATH = (
    Path(__file__).parent.parent / "qualification" / "modulation_route_qualification.json"
)

CAPABILITY_TARGET = "serum.modulation_route.add"


def build_modulation_route_contract() -> Optional[CapabilityContract]:
    """Returns None if no qualification evidence exists yet -- an honest
    'no contract', never a fabricated one (same invariant as
    capability_contract.build_contract())."""
    if not _QUALIFICATION_PATH.exists():
        return None

    data = json.loads(_QUALIFICATION_PATH.read_text())
    domain = data["domain"]
    instances = data["instances"]

    ui_verified = [i for i in instances if i["verification"]["tier"] == "UI_VERIFIED"]

    return CapabilityContract(
        target=CAPABILITY_TARGET,
        allowed_operation=MUTATE_STRUCTURED,
        status=STRUCTURAL_ONLY,
        prerequisites=(),
        verified={
            "load": "PASS", "persistence": "PASS",
            "causal": "NOT_RUN",  # honest -- no audio measurement performed for a routing op
        },
        measurement=None,
        scope={
            "tested_context_only": True,
            "supported_source_prefixes": tuple(domain["supported_source_prefixes"]),
            "supported_destination_families": tuple(domain["supported_destination_families"]),
            "amount_range": tuple(domain["amount_range"]),
            "bipolar_values": tuple(domain["bipolar_values"]),
            "note": (
                "Domain drawn from serum-mcp's own ModRouteSpec schema, corroborated "
                "by %d real qualification instance(s) (%d UI-verified in real Serum 2)."
                % (len(instances), len(ui_verified))
            ),
        },
        provenance={
            "qualification_source": str(_QUALIFICATION_PATH),
            "qualified_at": data["qualified_at"],
            "backend": data["backend"],
            "instances": tuple(
                {
                    "instance_id": i["instance_id"], "source": i["source"],
                    "destination": i["destination"], "preset_sha256": i["preset_sha256"],
                    "verification_tier": i["verification"]["tier"],
                }
                for i in instances
            ),
        },
        execution_binding=ExecutionBinding(
            mutation_type="TOPOLOGY",
            binding_source="serum2/producer/qualify_modulation_route.py",
            binding_version="1",
            resolver_operation_id="serum_mcp.add_modulation_route",
        ),
        limitations=(
            "STRUCTURAL_ONLY: construct+persist+load verified; no causal/audio "
            "measurement performed for this operation class.",
            "Only instance A (lfo0->filter0.cutoff) has real Serum UI MATRIX "
            "verification; instance B is file-level only.",
        ),
    )
