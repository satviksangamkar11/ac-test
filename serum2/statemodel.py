"""Raw Serum 2.0.21 v8 processor-state structural model.

REPRESENTATION ONLY. Nothing here asserts what a field DOES -- that is
capability knowledge, established by experiment through the evidence system.
This module answers only: what structures exist, of what type, how often, with
what observed value ranges, and which are optional.

Sources:
  - the v8 skeleton captured from Serum itself (authoritative default shape)
  - the 997-preset corpus (observed occupancy, ranges, enum-like values)
"""
import glob
import os
import re
from collections import defaultdict

CORPUS_ROOTS = [
    r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets",
    r"D:\\",
]

SPARSE_DEFAULT = "default"


def _kind(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    if v is None:
        return "null"
    return type(v).__name__


def module_family(key: str) -> str:
    """'ModSlot30' -> 'ModSlot'. Indexed instances collapse to one family."""
    return re.sub(r"\d+$", "", key) or key


def instance_index(key: str):
    m = re.search(r"(\d+)$", key)
    return int(m.group(1)) if m else None


class FieldStat:
    __slots__ = ("path", "kinds", "count", "numeric_min", "numeric_max",
                 "string_values", "list_lengths")

    def __init__(self, path):
        self.path = path
        self.kinds = defaultdict(int)
        self.count = 0
        self.numeric_min = None
        self.numeric_max = None
        self.string_values = defaultdict(int)
        self.list_lengths = defaultdict(int)

    def observe(self, v):
        self.count += 1
        k = _kind(v)
        self.kinds[k] += 1
        if k in ("int", "float") and not isinstance(v, bool):
            self.numeric_min = v if self.numeric_min is None else min(self.numeric_min, v)
            self.numeric_max = v if self.numeric_max is None else max(self.numeric_max, v)
        elif k == "str":
            if len(self.string_values) < 64:
                self.string_values[v] += 1
        elif k == "list":
            self.list_lengths[len(v)] += 1

    def summary(self):
        d = {
            "path": self.path,
            "observations": self.count,
            "types": dict(self.kinds),
        }
        if self.numeric_min is not None:
            d["observed_range"] = [self.numeric_min, self.numeric_max]
        if self.string_values:
            d["observed_strings"] = dict(sorted(self.string_values.items(),
                                                key=lambda kv: -kv[1])[:12])
            d["distinct_strings"] = len(self.string_values)
        if self.list_lengths:
            d["list_lengths"] = dict(self.list_lengths)
        return d


def walk(node, path, sink, max_depth=6, depth=0):
    """Record every leaf/container path. Indexed module names are normalised so
    ModSlot0..63 aggregate into one family path."""
    if depth > max_depth:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            fam = module_family(k) if depth == 0 else k
            p = "%s.%s" % (path, fam) if path else fam
            sink[p].observe(v)
            walk(v, p, sink, max_depth, depth + 1)
    elif isinstance(node, list):
        p = "%s[]" % path
        for item in node:
            sink[p].observe(item)
            walk(item, p, sink, max_depth, depth + 1)


def build(skeleton_body, corpus_bodies=None, max_depth=6):
    """Returns (skeleton_model, corpus_model). Skeleton = authoritative default
    shape from Serum. Corpus = observed occupancy across real presets."""
    skel = defaultdict(lambda: None)
    skel_sink = defaultdict(lambda: FieldStat(""))

    def sink_factory():
        d = {}

        class S(dict):
            def __missing__(self, key):
                self[key] = FieldStat(key)
                return self[key]
        return S()

    skel_sink = sink_factory()
    walk(skeleton_body, "", skel_sink, max_depth)

    corpus_sink = sink_factory()
    n_presets = 0
    for body in (corpus_bodies or []):
        n_presets += 1
        walk(body, "", corpus_sink, max_depth)

    return {
        "skeleton": {k: v.summary() for k, v in sorted(skel_sink.items())},
        "corpus": {k: v.summary() for k, v in sorted(corpus_sink.items())},
        "corpus_preset_count": n_presets,
    }


def module_families(skeleton_body):
    """Top-level families with their instance counts, from the skeleton."""
    fams = defaultdict(list)
    for k in skeleton_body:
        fams[module_family(k)].append(instance_index(k))
    out = {}
    for fam, idxs in sorted(fams.items()):
        real = [i for i in idxs if i is not None]
        out[fam] = {
            "instances": len(idxs),
            "indexed": bool(real),
            "index_range": [min(real), max(real)] if real else None,
        }
    return out


def sparse_occupancy(skeleton_body, corpus_bodies):
    """How often each top-level family is non-default across the corpus.
    Occupancy is an OBSERVATION about preset authorship, not about behaviour."""
    counts = defaultdict(int)
    totals = defaultdict(int)
    for body in corpus_bodies:
        for k, v in body.items():
            fam = module_family(k)
            totals[fam] += 1
            skel_v = skeleton_body.get(k)
            if skel_v is not None and v != skel_v:
                counts[fam] += 1
            elif skel_v is None and v not in (SPARSE_DEFAULT, {}, None):
                counts[fam] += 1
    return {fam: {"non_default": counts.get(fam, 0), "observed": totals[fam],
                  "rate": round(counts.get(fam, 0) / max(1, totals[fam]), 4)}
            for fam in sorted(totals)}


def corpus_paths(limit=None):
    files = []
    for root in CORPUS_ROOTS:
        files += glob.glob(os.path.join(root, "**", "*.SerumPreset"), recursive=True)
    files = sorted(set(files))
    return files[:limit] if limit else files
