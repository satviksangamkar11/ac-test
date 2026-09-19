"""Canonical target-name helpers shared by the Brain and event->request glue.

One place so 'Filter1.Cutoff' (census/timeline spelling) and 'Filter.Cutoff'
(Brain/MCP spelling) can never silently mean different things, and so a
target named in free text is found the same way everywhere.
"""
from __future__ import annotations

import re
from typing import List

_MODULES = r"(?:env|filter|osc|lfo|macro|global|fx|noise|sub|matrix|mixer|arp|clip)"
# a dotted control token such as Env1.Decay / Filter1.Type / OSCA.Enable (module prefix required,
# so ordinary text like "e.g." or "1.5" is never mistaken for a target)
_TOKEN_RE = re.compile(r"\b(%s[A-Za-z]*\d*)\.([A-Za-z][A-Za-z0-9_]*)\b" % _MODULES, re.IGNORECASE)
_OSC_LETTER = {"a": "1", "b": "2", "c": "3"}


def normalize_target_name(name: str) -> str:
    """'Filter1.Cutoff' -> 'filter.cutoff' (Filter 1 is the un-numbered Brain/MCP name);
    'OSCA.Enable' / 'oscA.enabled' / 'Osc1.Enable' -> 'osc1.enable'. Case-folded.
    Filter 2, other envelopes/oscillators keep their number, so they can never alias Filter 1 / Osc A."""
    n = (name or "").strip().lower()
    mod, _, field = n.partition(".")
    if mod == "filter1":
        mod = "filter"
    m = re.fullmatch(r"osc([abc])", mod)
    if m:
        mod = "osc" + _OSC_LETTER[m.group(1)]
    if field == "enabled":
        field = "enable"
    return mod + ("." + field if field else "")


def find_target_tokens(text: str) -> List[str]:
    """Normalized canonical targets named in free text, in order, de-duplicated."""
    out: List[str] = []
    for m in _TOKEN_RE.finditer(text or ""):
        t = normalize_target_name(m.group(0))
        if t not in out:
            out.append(t)
    return out


def find_surface_tokens(text: str) -> List[str]:
    """Dotted control tokens exactly as written (original spelling), de-duplicated case-insensitively,
    so the reference Atlas resolves what the request literally says."""
    out: List[str] = []
    seen = set()
    for m in _TOKEN_RE.finditer(text or ""):
        if m.group(0).lower() not in seen:
            seen.add(m.group(0).lower())
            out.append(m.group(0))
    return out
