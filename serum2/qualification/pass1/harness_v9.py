"""Serum 2.0.23 epoch adapter for the (unmodified) older-repo evidence harness.

The harness hard-codes processor state version 8.0 (Serum 2.0.21). The installed Serum is 2.0.23
(state version 9.0, binary sha pinned below). This adapter does NOT edit the older repo: it pins the
exact binary, checks the skeleton identity, and only then raises the in-process expected version.
Evidence recorded through it carries the new binary's sha in its own epoch, so it is a separate
epoch from every 2.0.21 record and can never be confused with one.

The adapter is only trustworthy if the positive controls (run_positive_controls.py) reproduce known
effects on this binary; Pass 1 must not be run before they pass.
"""
import hashlib
import sys

sys.path.insert(0, r"D:\ableton claude")

PINNED_SERUM_SHA256 = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"
PINNED_PRODUCT_VERSION = "2.0.23"
PINNED_STATE_VERSION = 9.0


def enable():
    from serum2 import bridge, processor_state
    from serum2.evidence import epoch
    sha = hashlib.sha256(open(epoch.SERUM_BINARY, "rb").read()).hexdigest()
    if sha != PINNED_SERUM_SHA256:
        raise RuntimeError("Serum binary changed again (%s); refusing to run on an unpinned build" % sha)
    meta, body = bridge.capture_v8_skeleton(epoch.SERUM_VST3)
    if meta.get("productVersion") != PINNED_PRODUCT_VERSION or float(meta.get("version")) != PINNED_STATE_VERSION:
        raise RuntimeError("unexpected skeleton identity: %r" % {k: meta.get(k) for k in ("productVersion", "version")})
    if len(body) != 162:
        raise RuntimeError("skeleton body has %d keys, expected 162" % len(body))
    processor_state.PROCESSOR_VERSION = PINNED_STATE_VERSION
    return {"serum_sha256": sha, "product_version": PINNED_PRODUCT_VERSION, "state_version": PINNED_STATE_VERSION}
