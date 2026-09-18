"""Canonical evidence digest."""

import hashlib
import json
from typing import Any, Dict

def digest(evidence: Dict[str, Any]) -> str:
    """Create a canonical digest of an evidence record."""
    # Simple SHA256 digest of JSON-serialized evidence
    serialized = json.dumps(evidence, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]
