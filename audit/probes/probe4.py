import sys, json
sys.path[:0] = ['.', 'serum2/knowledge']
import serum2.producer.execution_epoch as ee
E23 = [e for e in ee.KNOWN_EPOCHS if e.serum_version.startswith("2.0.23")][0]
ee.installed_epoch = lambda *a, **k: E23
import serum2.qualification.evidence_promotion as ep; ep.installed_epoch = ee.installed_epoch
from serum2.producer.producer_brain import execute_producer_request, ProducerRequest
for intent in ["set Env1.Attack to 1.5 ms", "Env2 decay 300 ms", "turn OSC B on", "set Filter 1 cutoff to 800 Hz"]:
    try:
        r = execute_producer_request(ProducerRequest(user_intent=intent, mode="EXECUTE", visual_mode="NEVER"), epoch=E23)
        d = r.__dict__; p = d.get("_serum_preset_plan") or {}
        print(intent, "->", d.get("execution_status"), "|", {k: p.get(k) for k in ("status","reason","mutation_target_path","mutation_value_used")})
    except Exception as e:
        import traceback; print(intent, "CRASH", type(e).__name__, e); traceback.print_exc(limit=-2)
