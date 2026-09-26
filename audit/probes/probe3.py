import sys, json, os, tempfile
sys.path[:0] = ['.', 'serum2/knowledge']
import serum2.producer.execution_epoch as ee
E23 = [e for e in ee.KNOWN_EPOCHS if e.serum_version.startswith("2.0.23")][0]
ee.installed_epoch = lambda *a, **k: E23
import serum2.qualification.evidence_promotion as ep; ep.installed_epoch = ee.installed_epoch
import serum2.server.reference_reproduction as rr
d = tempfile.mkdtemp()
# 300 acquired frames; the census "fills" exactly ONE of them with ONE control. 299 frames never analysed.
frames = [{"timestamp_sec": float(i), "serum_visible": None, "controls": [], "mod_routes": [], "observations": [], "unknown": []} for i in range(300)]
frames[150]["serum_visible"] = True
frames[150]["controls"] = [{"control_id": "env2.decay", "value": "300", "unit": "ms", "status": "OBSERVED", "control_type": "knob"}]
p = os.path.join(d, "stage_a.json"); json.dump({"frames": frames}, open(p, "w"))
sys.path.insert(0, "youtube_to_serum"); from reference_engine import stage_a_is_filled
print("stage_a_is_filled with 1/300 frames analysed:", stage_a_is_filled(p))
rl = os.path.join(d, "reread.json"); json.dump({"attempts": []}, open(rl, "w"))
ui = {"route": "DIRECT_UI", "captured_at": "typed-by-hand", "values": {"env2.decay": "300"}}
run = rr.run_reference_reproduction(p, rl, source={"video_id": "X"}, name="probe", epoch=E23, ui_readback=ui,
        promoted_evidence_dir="parameter_characterization/binding_evidence_mcp_exec_v1")
print("level:", run.verification_level, "| coverage:", run.coverage_status, "| reference_verified:", run.reference_verified)
print("preset:", run.preset["path"]); print("coverage():", rr.coverage(run))
