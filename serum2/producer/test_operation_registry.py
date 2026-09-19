"""Tests for operation_registry.py -- Phase C.

Proves the registry cross-checks `qualified` against the REAL
ContractRegistry (not hand-typed per entry -- a real bug this file caught
live: serum.modulation_route.add's static default under-reported
qualified=False despite a real contract existing).
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_registry_lists_both_domains():
    from serum2.producer.operation_registry import OperationRegistry
    r = OperationRegistry()
    domains = {op.domain for op in r.all_operations()}
    assert domains == {"SERUM", "ABLETON"}
    print("[PASS] test_registry_lists_both_domains")


def test_qualified_flag_is_cross_checked_not_hardcoded():
    """serum.modulation_route.add has a REAL qualified contract (built this
    session) -- the registry must report qualified=True by actually
    checking ContractRegistry, not by trusting a static per-entry default."""
    from serum2.producer.operation_registry import OperationRegistry
    r = OperationRegistry()
    op = r.get("SERUM.add_modulation_route")
    assert op is not None
    assert op.qualified is True, "must be cross-checked True against the real ContractRegistry"
    print("[PASS] test_qualified_flag_is_cross_checked_not_hardcoded")


def test_unqualified_operations_stay_honestly_unqualified():
    """No qualification evidence exists for these -- must never silently
    read as qualified just because they're declared."""
    from serum2.producer.operation_registry import OperationRegistry
    r = OperationRegistry()
    for op_id in ("SERUM.remove_modulation_route", "SERUM.set_enum",
                  "SERUM.configure_envelope", "SERUM.load_preset"):
        op = r.get(op_id)
        assert op is not None
        assert op.qualified is False, "%s must be honestly unqualified" % op_id
    print("[PASS] test_unqualified_operations_stay_honestly_unqualified")


def test_ableton_host_operations_have_no_capability_requirement():
    """Track/clip/note creation is not a Serum capability claim -- matches
    the existing _is_host_operation() architecture note in producer_brain.py."""
    from serum2.producer.operation_registry import OperationRegistry
    r = OperationRegistry()
    for op in r.by_domain("ABLETON"):
        assert op.capability_requirement is None
    print("[PASS] test_ableton_host_operations_have_no_capability_requirement")


def test_unknown_operation_id_returns_none_not_a_guess():
    from serum2.producer.operation_registry import OperationRegistry
    r = OperationRegistry()
    assert r.get("SERUM.made_up_operation") is None
    print("[PASS] test_unknown_operation_id_returns_none_not_a_guess")


if __name__ == "__main__":
    test_registry_lists_both_domains()
    test_qualified_flag_is_cross_checked_not_hardcoded()
    test_unqualified_operations_stay_honestly_unqualified()
    test_ableton_host_operations_have_no_capability_requirement()
    test_unknown_operation_id_returns_none_not_a_guess()
    print("\nAll operation registry tests passed.")
