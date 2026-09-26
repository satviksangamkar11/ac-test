import sys, json, traceback
sys.path[:0] = ['.', 'serum2/knowledge']
import serum2.producer.execution_epoch as ee
E23 = [e for e in ee.KNOWN_EPOCHS if e.serum_version.startswith("2.0.23")][0]
ee.installed_epoch = lambda *a, **k: E23           # simulate the real Windows machine
import serum2.qualification.evidence_promotion as ep; ep.installed_epoch = ee.installed_epoch
from serum2.producer.state_ledger import build_all
from serum2.producer.state_admission import admit_rows
from serum2.producer.contract_registry import ContractRegistry
PROM = "parameter_characterization/binding_evidence_mcp_exec_v1"; BIND = "parameter_characterization/binding_evidence"
reg = ContractRegistry(epoch=E23, binding_evidence_dir=BIND, promoted_evidence_dir=PROM)
print("registry size", len(reg.contracts), "promoted loaded", len(reg.promotion_diagnostics.get("loaded",[])))
pl = [k for k,c in reg.contracts.items() if not (c.scope or {}).get("mutation_target_path")]
print("contracts WITHOUT mutation_target_path (pathless -> invisible to find_contract):", len(pl), "of", len(reg.contracts))
def frame(ts, controls): return {"timestamp_sec": ts, "controls": controls, "mod_routes": [], "observations": [], "unknown": []}
def c(cid, v, ct="knob", unit=None): return {"control_id": cid, "value": v, "status": "OBSERVED", "control_type": ct, **({"unit": unit} if unit else {})}
cases = {
 "env_only": [frame(1, [c("env1.attack","12","knob","ms"), c("oscA.enabled","On","toggle"), c("env2.sustain","60","knob","%")])],
 "fx_exception": [frame(1, [c("fx.compressor.ratio","4","knob")])],
 "macro_name": [frame(1, [c("macro1.name","Wobble","text")])],
 "global": [frame(1, [c("global.voice_priority","Low","dropdown")])],
}
for name, frames in cases.items():
    try:
        rows = build_all({"frames": frames})
        adm = admit_rows(rows, E23, BIND, PROM)
        print("\n==", name)
        for r in rows: print("  ", r.control_id, r.terminal, "|", r.admission, "|", (r.reason or "")[:110])
    except Exception as e:
        print("\n==", name, "CRASH:", type(e).__name__, e)
import collections
d = reg.promotion_diagnostics
print("\nPROMOTION DIAG:", {k: len(v) for k,v in d.items()})
print(collections.Counter(v.split(":")[0] for v in d["rejected_not_promoted"].values()))
print(collections.Counter(v for v in d["rejected_contract"].values()))
for f,v in list(d["rejected_not_promoted"].items())[:6]: print("  ", f.split('/')[-1], v[:150])
print("binding diag:", {k:(len(v) if hasattr(v,'__len__') else v) for k,v in reg.binding_diagnostics.items()})
print("excluded:", len(reg.excluded), collections.Counter(v.split(":")[0] for v in reg.excluded.values()))
print("non-pathless:", [ (k, reg.contracts[k].scope.get("mutation_target_path"), getattr(reg.contracts[k].execution_binding,'mutation_type',None)) for k in reg.contracts if (reg.contracts[k].scope or {}).get("mutation_target_path")])
print("\nBINDING INVALID:"); [print("  ", f.split('/')[-1], str(v)[:160]) for f,v in reg.binding_diagnostics["rejected_invalid_evidence"].items()]
