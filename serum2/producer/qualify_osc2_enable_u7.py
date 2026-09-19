"""Run the real U7 structural qualification for OSC2.Enable and persist the evidence.

planner (production mappings) -> StructuralQualificationRunner -> SerumMCPPresetBackend
-> serum-mcp describe_preset/edit_preset -> the dedicated .SerumPreset fixture.

Run: python -m serum2.producer.qualify_osc2_enable_u7
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from serum2.producer.batch_qualification_system import (
    QUALIFICATION_DIR,
    MutationSpec,
    QualificationPlanner,
    StructuralQualificationRunner,
)
from serum2.producer.serum_mcp_qualification_backend import SerumMCPPresetBackend

FIXTURE = (
    Path.home() / "Documents" / "Xfer" / "Serum 2 Presets" / "Presets" / "User"
    / "VLP1-Phase3B-OSC2Enable-Test.SerumPreset"
)
OUT = QUALIFICATION_DIR / "osc2_enable_u7_structural_qualification.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def main() -> dict:
    (q,) = [t for t in QualificationPlanner().plan().all_targets if t.target == "OSC2.Enable"]
    cand = q.candidate
    backend = SerumMCPPresetBackend(str(FIXTURE))
    sha_before = _sha(FIXTURE)
    target_value = not backend.read(cand)  # toggle away from whatever the file actually holds
    result = StructuralQualificationRunner(backend).run(
        cand, MutationSpec(target="OSC2.Enable", value=target_value, operation="toggle")
    )
    evidence = {
        "semantic_target": q.target,
        "capability_key": q.capability_key,
        "qualified_at": datetime.now(timezone.utc).isoformat(),
        "backend": "serum-mcp (serum_mcp.tools.describe_preset / edit_preset, in-process)",
        "route_type": cand.route_type.value,
        "resolver_operation_id": cand.binding.resolver_operation_id,
        "binding_source": cand.binding.binding_source,
        "fixture_preset_path": str(FIXTURE),
        "fixture_preset_sha256_before": sha_before,
        "fixture_preset_sha256_after": _sha(FIXTURE),
        "baseline": result.baseline,
        "mutation": {"value": target_value},
        "post_mutation": result.after_mutation,
        "reload": result.after_reload,
        "state_change_verified": result.state_changed,
        "persistence_verified": result.persistence_verified,
        "verification_level": result.verification_level,
        "status": result.status,
        "tier": "FILE_VERIFIED_ONLY",
        "run": result.to_dict(),
        "notes": (
            "File-level structural qualification through serum-mcp's tool implementations. "
            "No live Serum plugin and no audio; NOT CAUSAL_VERIFIED."
        ),
    }
    OUT.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    e = main()
    print(e["status"], e["verification_level"], e["baseline"], "->", e["post_mutation"], "->", e["reload"])
