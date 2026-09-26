import sys, json
sys.path[:0] = ['.', 'serum2/knowledge']
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer import execution_epoch as ee
print("EPOCHS:", [ (e.label, e.binary_sha256[:8]) for e in ee.KNOWN_EPOCHS])
reg = ContractRegistry()
c = reg.contracts.get("envelope_field_attack")
print("legacy attack contract scope:", c.scope, "\nstatus", c.status, "op", c.allowed_operation, "binding", c.execution_binding)
for intent in ["longer Env1.Attack to 1.5 ms", "set Env1.Attack to 900 ms", "Env1 attack 0"]:
    r = ProducerBrain().execute(ProducerRequest(user_intent=intent, mode="EXECUTE", visual_mode="NEVER"))
    d = r.__dict__ if hasattr(r,'__dict__') else r
    plan = d.get("serum_preset_plan") or d.get("plan") or {k:v for k,v in d.items() if 'plan' in k}
    print("\nINTENT", intent, "status", d.get("execution_status"))
    for k,v in d.items():
        if isinstance(v, dict) and "mutation_value_used" in json.dumps(v, default=str):
            print(k, json.dumps({kk: v.get(kk) for kk in ("status","mutation_target_path","mutation_value_used")}, default=str))
# epoch-set registry
e23 = [e for e in ee.KNOWN_EPOCHS if e.serum_version.startswith("2.0.23")][0]
reg23 = ContractRegistry(epoch=e23)
print("\nepoch 2.0.23 registry size", len(reg23.contracts), "attack present?", "envelope_field_attack" in reg23.contracts)
print("excluded attack reason:", reg23.excluded.get("envelope_field_attack"))
print("final contract epoch:", reg23.final_execution_contract_epoch, "exec_spec env1.attack under epoch:", bool(reg23.execution_spec("env1.attack")))
