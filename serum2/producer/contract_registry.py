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

    def __init__(self, include_pass1: bool = False):
        # include_pass1: opt-in to the Serum 2.0.23-epoch Pass-1 contracts. Off by default so the frozen
        # contract frontier (and every test pinned to it) is unchanged unless a caller asks for the expansion.
        self.include_pass1 = include_pass1
        self.contracts = {}
        self._host_param_mapping = self._load_host_param_mapping()
        self._body_state_mapping = self._load_body_state_mapping()
        self._load_fresh_contracts()

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
        if self.include_pass1 and pass1_path.exists():
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
