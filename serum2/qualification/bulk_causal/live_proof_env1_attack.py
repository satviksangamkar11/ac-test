"""Live agent-driven execution proof (Finish Line B runtime-consumption step, proof layer B).

Complements test_final_execution_contract_runtime.py (proof layer A, deterministic/offline). That
proof shows the real ProducerBrain/ContractRegistry chain admits `env1.attack` and attaches the
committed final_execution_contract_v1.json's execution evidence to the plan. THIS script performs
the actual live mutation the plan describes, against the real Serum 2.0.23 VST3 instance, using
the existing generic pieces only:

  - ProducerBrain.execute() for the admitted plan (same chain proof layer A exercises)
  - serum2.producer.execution_epoch for the epoch/SHA check (unmodified, not weakened)
  - run_mcp_execution_harness.LiveBackend for the real Serum load/state/host-text readback (the SAME
    generic backend the 330-row v2/v3 sweeps used -- no second loader is created here)
  - serum_mcp.preset.mapping.apply_spec + serum_mcp.preset.packer.pack_file for building the edited
    body and writing it as a genuine, round-trippable .SerumPreset container (the same generic
    packer the campaign/sweep code writes presets with -- not a hand-rolled JSON dump)

It does NOT re-run the 330-control sweep, the promotion campaign, or any characterization work: it
runs the plan for exactly the one atlas_id named in the task, once.

ENVIRONMENT NOTE: LiveBackend only works on the machine that hosts the real Serum2.vst3 binary (see
run_mcp_execution_harness.LiveBackend's docstring/import path). This repository's cloud/CI container
has no such binary and no DawDreamer install (verified: `import dawdreamer` fails, no *.vst3 file
exists on this container). Running this script here reaches the real, unweakened epoch check
(serum2.producer.execution_epoch.installed_epoch) and fails there with FileNotFoundError -- before
any Serum call, MCP call, or preset write happens -- and reports that honestly rather than
fabricating a live result. The apply_spec/with_field/pack_file/unpack_file steps (building the
edited PresetSpec and writing+round-tripping a real .SerumPreset) were verified to work correctly in
this container using the existing generic pieces; only the LiveBackend load into a real Serum
instance and the true MCP tool call require the orchestrating agent's Serum-attached machine. See
the proof report for the full honest record.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

ATLAS_ID = "env1.attack"
EPOCH_VERSION = "2.0.23"
EPOCH_SHA256 = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"
OUT_PATH = REPO / "parameter_characterization" / "bulk_causal_evidence" / "env1_attack_live_proof_v1.json"


def build_admitted_plan():
    """Proof layer A's own chain: real ProducerBrain -> admitted Serum preset plan, carrying both
    the CapabilityContract authority fields and the final-contract execution-evidence fields."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    r = ProducerBrain().execute(ProducerRequest(
        user_intent="longer Env1.Attack to 1.5 ms", mode="EXECUTE", visual_mode="NEVER"))
    if not r.admitted or r._serum_preset_plan.get("status") != "SERUM_PRESET_PLAN_READY":
        raise RuntimeError("env1.attack was not admitted by the real chain: %r" % r.execution_status)
    return r._serum_preset_plan


def check_epoch():
    """Existing epoch machinery, unmodified and unweakened: refuses to proceed unless the installed
    Serum binary is exactly the 2.0.23 / 9293eb90... epoch this contract was proven against."""
    from serum2.producer.execution_epoch import installed_epoch, EPOCH_2_0_23
    epoch = installed_epoch()  # raises UnknownEpoch if the installed binary's sha is not a known epoch
    if epoch.binary_sha256 != EPOCH_2_0_23.binary_sha256 or epoch.serum_version != EPOCH_2_0_23.serum_version:
        raise RuntimeError("installed Serum epoch %s does not match the required %s" % (epoch, EPOCH_2_0_23))
    assert (epoch.serum_version, epoch.binary_sha256) == (EPOCH_VERSION, EPOCH_SHA256)
    return epoch


def run_live(plan):
    """The actual mutation, via the existing generic loader only. Returns the evidence record;
    never fabricates -- every field is a real captured value or the run fails outright."""
    import run_mcp_execution_harness as h  # the existing harness module; LiveBackend only, no new loader
    from campaign_derive import base_spec, with_field
    from preset_build import BASE
    from serum_mcp.preset.mapping import apply_spec
    from serum_mcp.preset.packer import SerumPreset, pack_file  # the existing generic Serum preset writer

    epoch = check_epoch()
    backend = h.LiveBackend()
    if backend.serum_sha256 != epoch.binary_sha256:
        raise RuntimeError("LiveBackend's own binary read (%s) disagrees with installed_epoch()" % backend.serum_sha256)

    fc = plan["final_execution_contract"]
    edit = fc["mcp_operation"]["edit"]
    leaf = fc["expected_raw"][0]  # env1.attack has exactly one raw leaf
    path, expected_value = leaf["path"], leaf["value"]

    baseline_spec = base_spec()
    baseline_body = apply_spec(BASE.data, baseline_spec)
    edited_spec = with_field(baseline_spec, edit, edit["value"])
    edited_body = apply_spec(BASE.data, edited_spec)

    backend.load(baseline_body)
    pre_state = backend.state()
    pre_leaf = h.body_get(pre_state, path)

    backend.load(edited_body)
    post_state = backend.state()
    post_leaf = h.body_get(post_state, path)
    post_hosts = backend.hosts()

    backend.load(baseline_body)  # restore
    restored_state = backend.state()
    restored_leaf = h.body_get(restored_state, path)

    # The SAME generic Serum preset writer the 330-row sweeps used (serum_mcp.preset.packer),
    # not a hand-rolled JSON dump -- this is a real, loadable .SerumPreset container.
    preset_path = OUT_PATH.with_suffix(".SerumPreset")
    pack_file(SerumPreset(metadata=BASE.metadata, data=edited_body), preset_path)
    preset_sha256 = hashlib.sha256(preset_path.read_bytes()).hexdigest()

    return {
        "atlas_id": ATLAS_ID,
        "final_contract_source_path": fc["source_path"],
        "final_contract_execution_metadata_used": fc,
        "capability_contract_authority_metadata_used": {
            "contract_id": plan["contract_id"],
            "mutation_target_path": plan["mutation_target_path"],
            "mutation_value_used": plan["mutation_value_used"],
        },
        "generated_preset_path": str(preset_path),
        "preset_sha256": preset_sha256,
        "serum_version": epoch.serum_version,
        "serum_binary_sha256": epoch.binary_sha256,
        "mcp_result": {"pre": pre_leaf, "post": post_leaf, "expected": expected_value,
                       "persisted": post_leaf == expected_value},
        "raw_readback": {"path": path, "pre": pre_leaf, "post": post_leaf},
        "expected_raw_value_from_final_contract": expected_value,
        "host_text_named_change": post_hosts.get("Env 1 Attack"),
        "restoration": {"pre": pre_leaf, "restored": restored_leaf, "restoration_verified": restored_leaf == pre_leaf},
    }


def main():
    plan = build_admitted_plan()
    try:
        record = run_live(plan)
    except (ModuleNotFoundError, FileNotFoundError) as e:
        record = {
            "atlas_id": ATLAS_ID,
            "status": "NOT_RUN_NO_LIVE_SERUM_IN_THIS_ENVIRONMENT",
            "reason": "%s: %s" % (type(e).__name__, e),
            "admitted_plan": plan,
            "note": "This container has no DawDreamer install and no Serum2.vst3 binary; run this "
                    "script on the orchestrating agent's Serum-attached machine to produce the live record.",
        }
    OUT_PATH.write_text(json.dumps(record, indent=1))
    print(json.dumps(record, indent=1, default=str))


if __name__ == "__main__":
    main()
