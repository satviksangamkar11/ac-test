"""ReferenceReproductionRun: the canonical VIDEO -> verified .SerumPreset path (RECREATE_REFERENCE).

Separate from the creation pipeline (transcript -> intent -> Brain -> generate). Literal observed state is not
reinterpreted by the Brain; it travels

  Stage-A evidence -> state ledger -> typed operations -> Atlas identity -> capability resolution (this run's
  Serum epoch only) -> admit() -> AuthorizedOperation -> generic compiler -> .SerumPreset -> FILE readback ->
  (real Serum load) -> DIRECT_UI readback -> normalized comparison -> verification level.

Only LIVE_UI_VERIFIED runs are eligible to become a verified episode; a file that matches itself is never
promoted. The run records replay pins (evidence hash, binding-table hash, contract identities, compiler hash,
Serum epoch) so a later replay can be checked against exactly what authorized this run.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from serum2.execution.authorized_state_compiler import compile_ops, ops_from_rows
from serum2.execution.state_comparator import compare_file, compare_ui, read_back_file, serialize, verification_level
from serum2.producer.execution_epoch import ExecutionEpoch, installed_epoch
from serum2.producer.state_admission import admit_rows
from serum2.producer.state_ledger import DERIVED, build_all, conservation, TABLE_PATH

ROOT = Path(__file__).resolve().parents[2]


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@dataclass
class ReferenceReproductionRun:
    source: Dict[str, Any]
    epoch: ExecutionEpoch
    evidence: Dict[str, str]
    ledger: Dict[str, Any]
    operations: List[Dict[str, Any]]
    admission: List[Dict[str, Any]]
    authorized: List[str]
    compilation: Dict[str, Any]
    preset: Dict[str, Any]
    file_comparison: Dict[str, Any]
    ui_comparison: Optional[Dict[str, Any]]
    verification_level: str
    replay_pins: Dict[str, Any]
    rows: List[Any] = field(default_factory=list, repr=False)

    @property
    def episode_eligible(self) -> bool:
        return self.verification_level == "LIVE_UI_VERIFIED"

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "epoch": self.epoch.label, "evidence": self.evidence, "ledger": self.ledger,
                "operations": self.operations, "admission": self.admission, "authorized": self.authorized,
                "compilation": self.compilation, "preset": self.preset, "file_comparison": self.file_comparison,
                "ui_comparison": self.ui_comparison, "verification_level": self.verification_level,
                "episode_eligible": self.episode_eligible, "replay_pins": self.replay_pins}


def run_reference_reproduction(stage_a_path, reread_log_path, corrections_path=None, *, source: Dict[str, Any], name: str,
                               epoch: Optional[ExecutionEpoch] = None, ui_readback: Optional[Dict[str, Any]] = None,
                               subfolder: str = "VLP1") -> ReferenceReproductionRun:
    epoch = epoch or installed_epoch()
    stage_a = json.loads(Path(stage_a_path).read_text(encoding="utf-8"))
    reread = json.loads(Path(reread_log_path).read_text(encoding="utf-8"))

    corrections = json.loads(Path(corrections_path).read_text(encoding="utf-8")) if corrections_path else None
    rows = build_all(stage_a, reread, corrections)
    ledger = conservation(stage_a, rows, corrections)
    if not ledger["invariant_holds"]:
        raise RuntimeError("ledger conservation invariant violated: %s" % ledger)
    admission = admit_rows(rows, epoch)
    ops = ops_from_rows(rows, epoch)
    report = compile_ops(ops, name, "reference reproduction of %s; every operand from an admitted observation" % source.get("video_id"), epoch)
    path = serialize(report, subfolder)
    file_cmp = compare_file(rows, read_back_file(path), report)
    ui_cmp = compare_ui(rows, ui_readback, report) if ui_readback else None
    level = verification_level(file_cmp, ui_cmp)

    from serum2.producer.contract_registry import ContractRegistry
    reg = ContractRegistry(epoch=epoch)
    pins = {
        "serum_epoch": epoch.label, "serum_binary_sha256": epoch.binary_sha256,
        "binding_table_sha256": _sha(TABLE_PATH),
        "compiler_sha256": _sha(ROOT / "serum2" / "execution" / "authorized_state_compiler.py"),
        "contracts": {o.contract_key: {"status": o.admission_evidence["contract_status"], "epoch": o.contract_epoch[:8],
                                       "binding": o.contract_binding, "execution_path": o.execution_path}
                      for o in ops},
        "registry_size": len(reg.contracts), "registry_excluded": dict(reg.excluded),
    }
    return ReferenceReproductionRun(
        source=source, epoch=epoch,
        evidence={"stage_a_sha256": _sha(stage_a_path), "reread_log_sha256": _sha(reread_log_path),
                  **({"stage_a_corrections_sha256": _sha(corrections_path)} if corrections_path else {})},
        ledger=ledger,
        operations=[{"control": r.control_id, "rack": r.context.get("rack"), "operation": r.op["operation"],
                     "operand": r.op.get("value", r.op.get("amount"))} for r in rows if r.terminal == DERIVED],
        admission=admission, authorized=[o.operation_id for o in ops],
        compilation={"status": report.status, "admitted": report.admitted, "compiled": report.compiled, "missing": report.missing},
        preset={"path": path, "sha256": _sha(path)}, file_comparison=file_cmp, ui_comparison=ui_cmp,
        verification_level=level, replay_pins=pins, rows=rows)


def coverage(run: "ReferenceReproductionRun") -> Dict[str, Any]:
    """What the run did NOT reproduce, so a verified subset is never mistaken for a full copy."""
    rows = run.rows
    considered = [r for r in rows if r.terminal not in ("IGNORED_NAVIGATION", "NOT_SERUM_SURFACE")]
    return {
        "observed_serum_state_rows": len(considered),
        "derived_operations": sum(1 for r in rows if r.terminal == DERIVED),
        "authorized_and_compiled": len(run.authorized),
        "not_authorized_by_status": dict(Counter(r.admission for r in rows if r.terminal == DERIVED and r.admission != "ADMITTED")),
        "not_derived_by_terminal": dict(Counter(r.terminal for r in considered if r.terminal != DERIVED)),
        "fraction_of_observed_state_reproduced": round(len(run.authorized) / max(1, len(considered)), 4),
    }


REFERENCE_REPRODUCTION_KEY = "reference_reproduction"


class NotVerified(RuntimeError):
    pass


def to_experience_record(run: "ReferenceReproductionRun", ui_readback: Dict[str, Any], *, run_id: str):
    """A verified episode for a reference reproduction, using the EXISTING ProductionExperienceRecord and its
    readback/replay helpers (no competing schema). Refuses anything that is not LIVE_UI_VERIFIED."""
    from serum2.server.experience_record import (EvidenceStage, ProductionExperienceRecord, SerumMcpCallRecord,
                                                 SerumUiActionRecord, build_readback_record, stamp_reference_provenance,
                                                 stamp_replay_provenance)
    if not run.episode_eligible or not ui_readback or ui_readback.get("route") != "DIRECT_UI":
        raise NotVerified("only a LIVE_UI_VERIFIED run with a DIRECT_UI readback can become an episode (level=%s)" % run.verification_level)
    from serum2.producer.contract_registry import ContractRegistry
    watched = [o.canonical_target for o in _authorized_ops(run)]
    expected = {r.control_id: r.value for r in run.rows if r.control_id in watched}
    readback = build_readback_record(domain="serum", route="DIRECT_UI", plugin="Serum 2", version=run.epoch.serum_version,
                                     delivery_route="in-plugin preset browser (VST3 hosted in Ableton Live)", watched=watched,
                                     expected=expected, observed={k: ui_readback["values"].get(k) for k in watched},
                                     artifact=ui_readback.get("method"))
    rec = ProductionExperienceRecord(experience_id="exp_ref_%s" % run_id, run_id=run_id, source_id=run.source.get("video_id"),
                                     source_url=run.source.get("url"))
    stamp_reference_provenance(rec)
    rec.serum_mcp_call = SerumMcpCallRecord(
        tool="serum_mcp.generate_preset", args_specified={"authorized_operations": run.authorized},
        stage=EvidenceStage.VERIFIED.value, result={"compilation": run.compilation},
        preset_path=run.preset["path"], preset_sha256=run.preset["sha256"]).to_dict()
    rec.serum_ui_actions = [SerumUiActionRecord(action="verify", stage=EvidenceStage.VERIFIED.value, evidence=readback,
                                                controls_matched=readback["all_match"]).to_dict()]
    rec.outcome = {"status": "VERIFIED" if readback["all_match"] else "MISMATCH", "verification_level": run.verification_level,
                   "coverage": coverage(run)}
    rec.provenance[REFERENCE_REPRODUCTION_KEY] = {
        "source": run.source, "epoch": run.epoch.label, "evidence": run.evidence, "ledger_terminals": run.ledger["terminals"],
        "authorized": run.authorized,
        "authorized_operations": [{"target": o.canonical_target, "operation": o.operation, "operand": o.operand,
                                  "contract_key": o.contract_key, "binding": o.contract_binding, "fidelity": o.fidelity}
                                 for o in _authorized_ops(run)],
        "file_comparison": run.file_comparison["field_counts"],
        "ui_comparison": run.ui_comparison["field_counts"], "verification_level": run.verification_level,
        "coverage": coverage(run), "replay_pins": run.replay_pins}
    keys = sorted({o.contract_key for o in _authorized_ops(run)})
    stamp_replay_provenance(rec, ContractRegistry(epoch=run.epoch), keys,
                            {"serum": {"version": run.epoch.serum_version, "binary_sha256": run.epoch.binary_sha256},
                             "compiler_sha256": run.replay_pins["compiler_sha256"],
                             "binding_table_sha256": run.replay_pins["binding_table_sha256"]},
                            [{"route": "DIRECT_UI", "plugin": "Serum 2", "version": run.epoch.serum_version}])
    return rec


def _authorized_ops(run):
    from serum2.execution.authorized_state_compiler import ops_from_rows
    return ops_from_rows(run.rows, run.epoch)
