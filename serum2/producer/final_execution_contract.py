"""Runtime reader for final_execution_contract_v1.json — the 330-row machine-readable
execution contract produced by build_final_execution_contract_v1.py.

This is the single authoritative source for MCP-exec-derived CapabilityContracts at
runtime. It is loaded by ContractRegistry BEFORE the individual promoted-evidence-dir
loader so the final contract takes precedence; the per-file evidence loader then skips
all 310 already-registered targets via its existing "target already registered" guard.

Authority boundary: this module only constructs CapabilityContracts. It never calls
admission.admit(), never mutates Serum, never marks anything "admitted". The
FinalExecutionContractIndex raises FileNotFoundError if the contract file is absent —
there is no silent fallback to the old evidence directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from serum2.evidence.capability_contract import (
    CapabilityContract, ExecutionBinding, STRUCTURAL_ONLY,
    MUTATE_NUMERIC, MUTATE_ENUM, MUTATE_BOOLEAN,
)

_REPO_ROOT = Path(__file__).parent.parent.parent
FINAL_CONTRACT_PATH = (
    _REPO_ROOT / "parameter_characterization" / "bulk_causal_evidence"
    / "final_execution_contract_v1.json"
)

PROMOTABLE_OUTCOMES = frozenset({
    "MCP_EXEC_HOST_CONFIRMED", "MCP_EXEC_CONFIRMED", "MCP_EXEC_RAW_ONLY",
})

_OP_TO_KIND = {
    MUTATE_NUMERIC: "mutate_numeric_value",
    MUTATE_ENUM: "mutate_enum_value",
    MUTATE_BOOLEAN: "mutate_boolean_value",
}


class FinalExecutionContractIndex:
    """Read-only index over final_execution_contract_v1.json.

    Raises FileNotFoundError on construction if the file is absent — never silently
    falls back to a stale or partial source.
    """

    def __init__(self, path=None):
        p = Path(path or FINAL_CONTRACT_PATH)
        if not p.exists():
            raise FileNotFoundError(
                "final_execution_contract_v1.json not found at %s — "
                "run build_final_execution_contract_v1.py first" % p
            )
        self._source_path = str(p.resolve())
        data = json.loads(p.read_text(encoding="utf-8"))
        self._by_atlas_id: Dict[str, dict] = {
            c["atlas_id"]: c for c in data["controls"]
        }
        self._summary = data.get("summary", {})

    @property
    def source_path(self) -> str:
        return self._source_path

    @property
    def epoch_sha256(self) -> Optional[str]:
        return self._summary.get("epoch_sha256")

    def get(self, atlas_id: str) -> Optional[dict]:
        """Return the raw row dict for atlas_id, or None."""
        return self._by_atlas_id.get(atlas_id)

    def is_known_exception(self, atlas_id: str) -> bool:
        row = self._by_atlas_id.get(atlas_id)
        return bool(row and row.get("known_exception"))

    def __len__(self) -> int:
        return len(self._by_atlas_id)


def _build_contract(row: dict, source_path: str) -> Optional[CapabilityContract]:
    """Build a CapabilityContract from one final-contract row.

    Returns None for rows the registry should not hold (exceptions, open items).
    Domain keys are normalized to match promote_verified_evidence's convention
    (scope.domain uses the allowed_operation string as kind, lo/hi for numeric).
    """
    if row.get("known_exception"):
        return None
    if row.get("execution_outcome") not in PROMOTABLE_OUTCOMES:
        return None

    op = row.get("allowed_operation")
    if op not in (MUTATE_NUMERIC, MUTATE_ENUM, MUTATE_BOOLEAN):
        return None

    vd = row.get("valid_domain") or {}
    if op == MUTATE_NUMERIC:
        domain = {"kind": op, "lo": vd.get("min"), "hi": vd.get("max")}
    elif op == MUTATE_ENUM:
        domain = {"kind": op, "enum_values": list(vd.get("values") or [])}
    else:
        domain = {"kind": op}

    binding = ExecutionBinding(
        mutation_type="SERUM_PRESET_STRUCTURAL",
        body_path=row.get("raw_body_path"),
        binding_source="final_execution_contract_v1.json",
        binding_version="v1",
    )

    return CapabilityContract(
        target=row["atlas_id"],
        allowed_operation=op,
        status=STRUCTURAL_ONLY,
        prerequisites=(),
        verified={"load": "PASS", "persistence": "PASS", "causal": "NOT_RUN"},
        measurement=None,
        scope={
            "domain": domain,
            "execution_outcome": row.get("execution_outcome"),
            "tested_context_only": True,
            "serum_binary_sha256": row.get("epoch_sha256"),
        },
        provenance={
            "promoted_from": "final_execution_contract_v1.json",
            "source_path": source_path,
        },
        limitations=(
            "STRUCTURAL_ONLY: proven via MCP execution harness "
            "(3-load persistence+restoration, real Serum 2.0.23 VST3), "
            "not an audio-measured causal effect",
        ),
        execution_binding=binding,
    )


def load_final_execution_contracts(
    path=None, epoch=None
) -> Tuple[Dict[str, CapabilityContract], Dict[str, Optional[str]], str]:
    """Load CapabilityContracts and known-exception metadata from the final contract.

    Args:
        path: override path to final_execution_contract_v1.json (None = default)
        epoch: ExecutionEpoch; if given, rows whose epoch_sha256 doesn't match are
               skipped with a diagnostic (epoch boundary is never crossed)

    Returns:
        contracts: Dict[atlas_id -> CapabilityContract] for executable rows
        exceptions: Dict[atlas_id -> Optional[exception_detail]] for exception rows
        source_path: absolute resolved path of the file that was read

    Raises:
        FileNotFoundError: if the contract file is absent (never silently falls back)
    """
    idx = FinalExecutionContractIndex(path)
    contracts: Dict[str, CapabilityContract] = {}
    exceptions: Dict[str, Optional[str]] = {}

    for atlas_id, row in idx._by_atlas_id.items():
        if epoch is not None:
            row_sha = row.get("epoch_sha256")
            if row_sha != epoch.binary_sha256:
                continue

        if row.get("known_exception"):
            exceptions[atlas_id] = row.get("exception_detail")
            continue

        contract = _build_contract(row, idx.source_path)
        if contract is not None:
            contracts[atlas_id] = contract

    return contracts, exceptions, idx.source_path
