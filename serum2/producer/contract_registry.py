"""Contract registry for canonical producer.

Unified access to fresh CapabilityContracts from 4.Q.4 qualifications.
Source of truth for which contracts are available to the producer.

Maps semantic targets to their CAUSAL_VERIFIED contracts.
Never falls back to design-JSON or archived contracts.
"""
import json
import pickle
import dataclasses
from typing import Optional, Dict, Tuple
from pathlib import Path

from serum2.evidence.capability_contract import CapabilityContract, ExecutionBinding


_PASS1_TARGETS = frozenset(
    ["oscillator_field_OSC2-ENABLE", "oscillator_field_OSC3-ENABLE",
     "oscillator_field_OSC2-OCTAVE", "oscillator_field_OSC3-OCTAVE"]
    + ["envelope%d_field_%s" % (n, f) for n in (2, 3, 4) for f in ("decay", "release")]
)


class ContractRegistry:
    """Unified registry for fresh CapabilityContracts.

    Loads contracts from 4.Q.4 pickle stores:
    - _capability_contracts_4_1.pkl (Release)
    - _capability_contracts_4_2.pkl (Attack)

    Never consults design-JSON or archived stores.

    D.1.2: Attaches ExecutionBinding to loaded contracts, derived from the
    authoritative semantic_vst3_mapping.json (the same source
    resolve_host_param_name() already uses). This does NOT edit the pickled
    evidence artifacts; it augments the in-memory contract object at load
    time via dataclasses.replace(), since CapabilityContract is frozen.
    """

    def __init__(self, epoch=None, binding_evidence_dir=None, promoted_evidence_dir=None):
        # epoch=None: the frozen legacy frontier, unchanged (every legacy test is pinned to it).
        # epoch=ExecutionEpoch: ONLY contracts qualified on that exact Serum build are loaded; everything
        # else is recorded in self.excluded with the reason. No contract crosses epochs.
        self.epoch = epoch
        self.excluded = {}
        self.contracts = {}
        self._host_param_mapping = self._load_host_param_mapping()
        self._body_state_mapping = self._load_body_state_mapping()
        self._load_fresh_contracts()
        self.binding_diagnostics = {}
        self._load_binding_evidence_contracts(binding_evidence_dir)
        self.promotion_diagnostics = {}
        self._load_promoted_evidence_contracts(promoted_evidence_dir)
        self.execution_specs = {}
        self._load_final_execution_contract()

    def _load_host_param_mapping(self) -> Dict[str, str]:
        """Load the authoritative capability_key -> host parameter name mapping.

        Same source used by canonical_feedback_loop.resolve_host_param_name().
        """
        mapping_path = Path(__file__).parent.parent / "qualification" / "semantic_vst3_mapping.json"
        try:
            with open(mapping_path) as f:
                data = json.load(f)
            return data.get("mappings", {})
        except FileNotFoundError:
            print(f"[ContractRegistry] Warning: mapping not found: {mapping_path}")
            return {}

    def _load_body_state_mapping(self) -> Dict[str, Dict]:
        """Load BODY_STATE execution bindings for targets that use direct path mutation.

        Source: body_state_mapping.json (Phase 3 FXEQ recovery).
        Returns dict: capability_key -> {mutation_type, body_path, ...}
        """
        mapping_path = Path(__file__).parent.parent / "qualification" / "body_state_mapping.json"
        try:
            with open(mapping_path) as f:
                data = json.load(f)
            return data.get("bindings", {})
        except FileNotFoundError:
            return {}

    def _attach_execution_binding(self, contract: CapabilityContract) -> CapabilityContract:
        """Derive and attach the authoritative ExecutionBinding for a contract.

        contract.target IS the capability_key (e.g. 'envelope_field_release').

        Checks binding sources in order:
        1. BODY_STATE: body_state_mapping.json (Phase 3 FXEQ recovery)
        2. HOST_PARAMETER: semantic_vst3_mapping.json (authoritative VST3 mappings)

        If no mapping entry exists, the contract is returned unchanged (execution_binding
        stays None) and the executor will correctly refuse it.
        """
        # Check BODY_STATE binding first
        body_state_binding = self._body_state_mapping.get(contract.target)
        if body_state_binding is not None:
            binding = ExecutionBinding(
                mutation_type="BODY_STATE",
                body_path=body_state_binding.get("body_path"),
                host_parameter_name=None,
                binding_source="body_state_mapping.json",
                binding_version=str(1),
            )
            return dataclasses.replace(contract, execution_binding=binding)

        # Check HOST_PARAMETER binding
        host_param_name = self._host_param_mapping.get(contract.target)
        if host_param_name is None:
            return contract

        binding = ExecutionBinding(
            mutation_type="HOST_PARAMETER",
            body_path=None,
            host_parameter_name=host_param_name,
            binding_source="semantic_vst3_mapping.json",
            binding_version=str(1),
        )
        return dataclasses.replace(contract, execution_binding=binding)

    def _load_binding_evidence_contracts(self, evidence_dir=None):
        """Evidence-derived contracts (candidate_binding_qualifier output), built by the generic ClaimEngine/build_contract
        path. Explicit opt-in (a directory must be named) and epoch runs only, so no run's authority widens implicitly;
        a target already present is never overridden."""
        if self.epoch is None or not evidence_dir:
            return
        from serum2.qualification.binding_contract import load_binding_contracts
        d = Path(evidence_dir)
        loaded, diag = load_binding_contracts(sorted(d.glob("*.json")) if d.is_dir() else [], self.epoch)
        for target, c in loaded.items():
            if target in self.contracts:
                diag["rejected_contract"][target] = "target already registered"
                diag["loaded"].remove(target)
            else:
                self.contracts[target] = c
        self.binding_diagnostics = diag

    def _load_promoted_evidence_contracts(self, evidence_dir=None):
        """A second, parallel evidence source: raw `serum2.qualification.evidence_promotion` input dicts (the
        MCP-execution / bulk-causal evidence shape -- target/epoch/status/body_diff_filtered/baseline_value/
        mutated_value), NOT the candidate_binding_qualifier shape `_load_binding_evidence_contracts` above consumes.
        Each file is re-validated through the existing pure `promote_verified_evidence` at load time -- no
        pre-built contract is ever trusted as-is. Explicit opt-in, epoch runs only, and a target already registered
        by any other source is never overridden (same rule as every other loader in this class)."""
        if self.epoch is None or not evidence_dir:
            return
        import json
        from serum2.qualification.evidence_promotion import promote_verified_evidence
        d = Path(evidence_dir)
        diag = {"loaded": [], "rejected_invalid_evidence": {}, "rejected_epoch": {}, "rejected_not_promoted": {}, "rejected_contract": {}}
        for f in sorted(d.glob("*.json")) if d.is_dir() else []:
            try:
                ev = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                diag["rejected_invalid_evidence"][str(f)] = "unreadable: %s" % e
                continue
            sha = (ev.get("epoch") or {}).get("serum_sha256")
            if sha != self.epoch.binary_sha256:
                diag["rejected_epoch"][str(f)] = "recorded %s, run epoch %s" % (str(sha)[:8], self.epoch.label)
                continue
            # promote_verified_evidence is documented as a pure function of one evidence dict -> PromotionResult;
            # it never raises (including when installed_epoch() can't resolve the machine's Serum binary -- that
            # comes back as an ordinary REJECT_EPOCH_MISMATCH result, not an exception).
            result = promote_verified_evidence(ev)
            if not result.promoted:
                diag["rejected_not_promoted"][str(f)] = "%s: %s" % (result.reason, result.detail)
                continue
            target = result.contract.target
            if target in self.contracts:
                diag["rejected_contract"][str(f)] = "target already registered"
                continue
            self.contracts[target] = result.contract
            diag["loaded"].append(target)
        self.promotion_diagnostics = diag

    def _attach_pass1_binding(self, contract):
        """Attach an ExecutionBinding ONLY from a BINDING_VERIFIED evidence file whose accessor was proven to
        write this contract's own mutation_target_path (see qualification/pass1/qualify_bindings_pass1.py).
        No evidence file -> no binding (the contract stays unbound, never guessed)."""
        import json
        ev_path = Path(__file__).parent.parent / "qualification" / "pass1" / "bindings" / (contract.target + ".json")
        try:
            ev = json.loads(ev_path.read_text())
        except Exception:
            return contract
        if (ev.get("status") != "BINDING_VERIFIED" or not ev.get("accessor_writes_contract_body_path")
                or ev.get("contract_body_path") != (contract.scope or {}).get("mutation_target_path")):
            return contract
        binding = ExecutionBinding(
            mutation_type="SERUM_PRESET_STRUCTURAL", body_path=ev["contract_body_path"],
            binding_source="serum2/qualification/pass1/bindings/%s.json" % contract.target,
            binding_version="pass1-2.0.23", resolver_operation_id=ev["accessor"])
        return dataclasses.replace(contract, execution_binding=binding)

    def _load_fresh_contracts(self):
        """Load fresh contracts from 4.Q.4 qualification pickle stores + canonical restored store."""
        base_path = Path(__file__).parent.parent.parent / "experiments"

        # Load 4.1 Release contract
        store_4_1_path = base_path / "_capability_contracts_4_1.pkl"
        if store_4_1_path.exists():
            try:
                with open(store_4_1_path, 'rb') as f:
                    store_4_1 = pickle.load(f)
                    for (claim_id, sig_hash), contract in store_4_1.items():
                        if contract.target == 'envelope_field_release':
                            contract = self._attach_execution_binding(contract)
                            self.contracts['envelope_field_release'] = contract
                            print(f"[ContractRegistry] Loaded Release contract: {contract.status}")
            except Exception as e:
                print(f"[ContractRegistry] Warning: Could not load Release contract: {e}")
        else:
            print(f"[ContractRegistry] Warning: Release contract store not found: {store_4_1_path}")

        # Load 4.2 Attack contract
        store_4_2_path = base_path / "_capability_contracts_4_2.pkl"
        if store_4_2_path.exists():
            try:
                with open(store_4_2_path, 'rb') as f:
                    store_4_2 = pickle.load(f)
                    for (claim_id, sig_hash), contract in store_4_2.items():
                        if contract.target == 'envelope_field_attack':
                            contract = self._attach_execution_binding(contract)
                            self.contracts['envelope_field_attack'] = contract
                            print(f"[ContractRegistry] Loaded Attack contract: {contract.status}")
            except Exception as e:
                print(f"[ContractRegistry] Warning: Could not load Attack contract: {e}")
        else:
            print(f"[ContractRegistry] Warning: Attack contract store not found: {store_4_2_path}")

        # Load Phase 3: canonical restored store (11 Phase 2 admitted targets + 26 Phase 1+original)
        canonical_path = base_path / "_capability_contracts.pkl"
        if canonical_path.exists():
            try:
                with open(canonical_path, 'rb') as f:
                    canonical_store = pickle.load(f)
                    loaded_count = 0
                    for contract in canonical_store.values():
                        if contract.status == "CAUSAL_VERIFIED":
                            contract = self._attach_execution_binding(contract)
                            self.contracts[contract.target] = contract
                            loaded_count += 1
                    print(f"[ContractRegistry] Loaded {loaded_count} CAUSAL_VERIFIED from canonical store")
            except Exception as e:
                print(f"[ContractRegistry] Warning: Could not load canonical store: {e}")
        else:
            print(f"[ContractRegistry] Note: Canonical store not found: {canonical_path}")

        # Authority-expansion Pass 1 (Serum 2.0.23 epoch): fresh contracts built by
        # serum2/qualification/pass1/build_pass1_contracts.py through the unmodified
        # ClaimEngine/build_contract. Explicit allow-list; never overwrites an existing
        # contract; each must carry the epoch it was proven in.
        pass1_path = base_path / "_capability_contracts_pass1.pkl"
        legacy_keys = set(self.contracts)
        if self.epoch is not None and pass1_path.exists():
            try:
                with open(pass1_path, 'rb') as f:
                    pass1_store = pickle.load(f)
                loaded_pass1 = 0
                for contract in pass1_store.values():
                    if (contract.target in _PASS1_TARGETS
                            and contract.status in ("CAUSAL_VERIFIED", "STRUCTURAL_ONLY")
                            and contract.scope.get("serum_binary_sha256")
                            and contract.target not in self.contracts):
                        contract = self._attach_pass1_binding(contract)
                        self.contracts[contract.target] = contract
                        loaded_pass1 += 1
                print(f"[ContractRegistry] Loaded {loaded_pass1} Pass-1 contracts (Serum 2.0.23 epoch)")
            except Exception as e:
                print(f"[ContractRegistry] Warning: Could not load Pass-1 contracts: {e}")

        # Load the generic modulation-route capability, derived from real
        # qualification evidence (serum2/producer/qualify_modulation_route.py)
        # -- not from a pickle store, since this is a new capability class,
        # not part of the historical 4.Q/canonical campaigns.
        try:
            from serum2.producer.modulation_route_contract import (
                build_modulation_route_contract, CAPABILITY_TARGET,
            )
            contract = build_modulation_route_contract()
            if contract is not None:
                self.contracts[CAPABILITY_TARGET] = contract
                print(f"[ContractRegistry] Loaded {CAPABILITY_TARGET} contract: {contract.status}")
        except Exception as e:
            print(f"[ContractRegistry] Warning: Could not load modulation-route contract: {e}")

        self._apply_epoch(legacy_keys)

    def _apply_epoch(self, legacy_keys):
        """Tag each contract with the epoch it was proven on and drop every contract not proven on self.epoch."""
        if self.epoch is None:
            return
        from serum2.producer.execution_epoch import EPOCH_2_0_21, epoch_for_sha
        kept = {}
        for target, c in self.contracts.items():
            scope = dict(c.scope or {})
            sha = scope.get("serum_binary_sha256")
            if sha:
                source = "recorded in contract scope"
            elif target in legacy_keys:
                sha, source = EPOCH_2_0_21.binary_sha256, (
                    "inferred: every archived EvidenceRecord (65) carries sha 7978c9be, none any other")
            else:
                self.excluded[target] = "epoch not recorded and not inferable"
                continue
            e = epoch_for_sha(sha)
            if sha != self.epoch.binary_sha256:
                self.excluded[target] = "EPOCH_MISMATCH: proven on %s, run epoch is %s" % (
                    e.label if e else sha[:8], self.epoch.label)
                continue
            scope.update({"serum_binary_sha256": sha, "serum_product_version": self.epoch.serum_version,
                          "epoch_source": source})
            kept[target] = dataclasses.replace(c, scope=scope)
        self.contracts = kept

    def get_contracts_dict(self) -> Dict[Tuple[str, str], CapabilityContract]:
        """Return contracts in format expected by admission.admit().

        admission.admit() expects Dict[(claim_id, condition_sig_hash) -> CapabilityContract]
        We reconstruct these keys from the contract's internal provenance.

        Returns:
            Dict mapping (claim_id, condition_sig_hash) to contract
        """
        result = {}
        for target, contract in self.contracts.items():
            # Extract claim_id from contract (set during build_contract)
            claim_id = getattr(contract, 'claim_definition_id', target)
            # Extract condition signature hash from scope
            sig_hash = contract.scope.get('condition_signature_hash', 'unknown')
            key = (claim_id, sig_hash)
            result[key] = contract
        return result

    # ------------------------------------------------------------------
    # Final execution contract (Finish Line B, live v3 sweep authority):
    # execution-EVIDENCE index only, keyed by the canonical Atlas atlas_id
    # (e.g. "env1.attack"). This is NOT a second CapabilityContract source
    # and NOT a parallel runtime-lookup subsystem: allowed_operation,
    # capability status, prerequisites and admission authority remain
    # exclusively on the CapabilityContract loaded above. This index only
    # answers "what did live MCP execution prove for this atlas_id" --
    # mcp_operation / expected_raw / declared_domain / final_execution_
    # classification / exception_policy -- for the producer to cross-check
    # against the authority contract's own scope, never to replace it.
    # ------------------------------------------------------------------
    FINAL_EXECUTION_CONTRACT_PATH = (
        Path(__file__).parent.parent.parent / "parameter_characterization"
        / "bulk_causal_evidence" / "final_execution_contract_v1.json"
    )

    def _load_final_execution_contract(self):
        path = self.FINAL_EXECUTION_CONTRACT_PATH
        try:
            doc = json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[ContractRegistry] Warning: final execution contract not loaded: {e}")
            return
        lookup = doc.get("producer_lookup", {})
        for row in doc.get("rows", ()):
            atlas_id = row["atlas_id"]
            pl = lookup.get(atlas_id, {})
            self.execution_specs[atlas_id] = {
                "atlas_id": atlas_id,
                "mcp_operation": row["mcp_operation"],
                "expected_raw": row["expected_raw"],
                "declared_domain": row.get("declared_domain"),
                "final_execution_classification": row["final_execution_classification"],
                "restoration_verified": row["restoration_verified"],
                "exception_policy": pl.get("exception_policy", "NONE"),
                "producer_lookup": pl,
                "source_path": str(path),
            }

    def execution_spec(self, atlas_id: Optional[str]) -> Optional[Dict]:
        """Live-execution evidence for one Atlas atlas_id, from the committed final execution
        contract only. None when atlas_id is None or has no row there -- never a fallback guess."""
        if not atlas_id:
            return None
        return self.execution_specs.get(atlas_id)

    def get(self, semantic_target: str) -> Optional[CapabilityContract]:
        """Get contract for a semantic target.

        Args:
            semantic_target: e.g., "envelope_field_release"

        Returns:
            CapabilityContract if available, None otherwise
        """
        return self.contracts.get(semantic_target)

    def all_targets(self) -> list:
        """Return list of all registered semantic targets."""
        return list(self.contracts.keys())
