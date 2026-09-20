"""Execution epoch: which Serum build a run executes on, and therefore which contracts may authorize it.

A contract is evidence about ONE Serum build. A run on build X may only be authorized by contracts
qualified on build X; a semantic-target match is never enough. Epoch identity is the binary's SHA-256
(version strings alone are not trusted).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

SERUM_BINARY = r"C:\Program Files\Common Files\VST3\Serum2.vst3\Contents\x86_64-win\Serum2.vst3"


@dataclass(frozen=True)
class ExecutionEpoch:
    serum_version: str
    binary_sha256: str
    processor_state_version: float

    @property
    def label(self) -> str:
        return "%s@%s" % (self.serum_version, self.binary_sha256[:8])


EPOCH_2_0_21 = ExecutionEpoch(
    "2.0.21", "7978c9be5b2107e985c24c174000faee87e11483ec989d81dc61b5829b45ed70", 8.0)
EPOCH_2_0_23 = ExecutionEpoch(
    "2.0.23", "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3", 9.0)
KNOWN_EPOCHS = (EPOCH_2_0_21, EPOCH_2_0_23)


class UnknownEpoch(RuntimeError):
    pass


def epoch_for_sha(sha: str) -> Optional[ExecutionEpoch]:
    return next((e for e in KNOWN_EPOCHS if e.binary_sha256 == sha), None)


def installed_epoch(binary: str = SERUM_BINARY) -> ExecutionEpoch:
    """The epoch of the Serum actually installed. Unknown binary -> refuse, never guess."""
    sha = hashlib.sha256(open(binary, "rb").read()).hexdigest()
    e = epoch_for_sha(sha)
    if e is None:
        raise UnknownEpoch("installed Serum binary %s is not a known qualified epoch" % sha)
    return e
