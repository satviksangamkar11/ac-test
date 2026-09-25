"""Minimal bulk DIRECT_UI verification set + the full 330-control Serum map. Generation only (no Serum, no rendering).

    python build_bulk_ui_verification.py

Outputs
  giant_verify_out/bulk_ui_verification/{BULK_*.SerumPreset, BULK_*.controls.json, index.json, OPTIMIZATION_REPORT.md}
  parameter_characterization/bulk_causal_evidence/serum_full_control_map_v1.json   (exactly 330 entries)

Method (all derived from repo evidence; nothing here writes to authority/binding/admission code):
  1. Accounting: campaign_accounting_v1 (330) x manifest (328 derived) x closure_ledger_v3 (causal + host-text + DIRECT_UI
     tiers, kept separate) x giant plan x the GUI campaign run x session-2 scan notes.
  2. Host crosswalk: CAUSAL first (host parameters whose text changed when exactly this raw leaf was written, from the
     campaign run), then NAME heuristics against the 412-parameter dump (module prefix + token overlap), each with a
     confidence and the ambiguous alternatives. Host indices are preserved.
  3. Workload: a control needs new DIRECT_UI work unless it is already UI_CONFIRMED. Controls with no valid raw value
     (NOT_DERIVED) or that Serum never stores are routed to residual operations, never to a preset.
  4. Batching: conflict graph over the remaining controls. Edges come from the only hard incompatibilities the evidence
     establishes: (a) oscillator engine mode (WTOsc controls need WAVETABLE, SampleOsc controls need SAMPLE on the same
     slot); (b) the LFO shape/mode coupling (mode=Envelope is disabled under shape=S&H; chaotic shapes' effect on
     Envelope is unknown, so shape tests and mode=Envelope tests never share an LFO). DSatur colouring gives the preset
     count; the max clique is the proven lower bound. Everything without an edge rides in the first preset.
  5. Fingerprints: per UI view, continuous values come from a golden-ratio low-discrepancy sequence over the safe
     interior [0.15, 0.85] of the declared domain (log domains in log space), rounded to display-friendly steps, and
     checked for minimum separation and for collisions with the default, the old giant target and each other; ints get
     distinct interior integers; enums rotate through non-default words so same-vocabulary controls in one view differ;
     bools flip; open domains use values Serum itself stored; texts are self-identifying.
"""
import copy
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import _leaves_for, body_get, body_set, resolve_path  # noqa: E402
from build_giant_verification_preset import FX_CONTEXTS_ORDER  # noqa: E402
from campaign_derive import leaves as diff_leaves  # noqa: E402
from closure_ledger import ED  # noqa: E402
from preset_build import BASE, SPEC0, pack_file, pack_unpack, unpack_file  # noqa: E402
from range_plan import close  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

GV = os.path.join(HERE, "giant_verify_out")
OUT = os.path.join(GV, "bulk_ui_verification")
MAP_OUT = os.path.join(ED, "serum_full_control_map_v1.json")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BT = os.path.join(REPO, "serum2", "reference", "serum_mcp_binding_table.json")
PHI = (math.sqrt(5) - 1) / 2
ANCHORS = ["env1.sustain", "env2.sustain", "env3.sustain", "env4.sustain", "fx.compressor.attack", "fx.compressor.gain",
           "fx.compressor.ratio", "fx.compressor.thresh", "fx.reverb.type", "arp.transpose.shape",
           "lfo1.mode", "lfo2.mode", "lfo3.mode", "lfo4.mode", "lfo5.mode", "lfo6.mode"] + \
          ["osc%s.%s" % (o, f) for o in "ABC" for f in ("warp_amount", "warp_mode", "warp_mode2", "warp_var2", "warp_amount2")]
# Session-2 hover readings of VERIFY_SECONDARY_OSC_WARP2 (ui_scan_2026-09-26.md, d0f75df): supplementary DIRECT_UI,
# recorded separately from direct_ui_evidence_v2.json (not merged into it). Only the controls whose preset value is known.
SESSION2 = {"osc%s.warp_amount2" % o: {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": 0.5, "screen": "50 %", "verdict": "MATCH"} for o in "ABC"}
SESSION2.update({"oscA.warp_mode": {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": "kFM_OSC", "screen": "FM (B)", "verdict": "NORMALIZED_MATCH"},
                 "oscB.warp_mode": {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": "kFM_OSC", "screen": "FM (A)", "verdict": "NORMALIZED_MATCH"},
                 "oscC.warp_mode": {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": "kFM_OSC", "screen": "FM (A)", "verdict": "NORMALIZED_MATCH"}})
SESSION2.update({"oscA.warp_mode2": {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": "kFM_OSC", "screen": "FM (B)", "verdict": "NORMALIZED_MATCH"},
                 "oscB.warp_mode2": {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": "kFM_OSC", "screen": "FM (A)", "verdict": "NORMALIZED_MATCH"},
                 "oscC.warp_mode2": {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": "kFM_OSC", "screen": "FM (A)", "verdict": "NORMALIZED_MATCH"}})
SESSION2.update({"osc%s.warp_amount" % o: {"preset": "VERIFY_SECONDARY_OSC_WARP2", "written": 0.0, "screen": "0 %",
                                           "verdict": "MATCH_AT_DEFAULT (weak: 0.0 is the default, so it proves nothing about the write)"} for o in "ABC"})
# screen-reading limits recorded by the scans (ui_scan_2026-09-26.md): controls with no hover tooltip / not located
NO_TOOLTIP = {"global.master_volume": "no tooltip", "fx.dimension.size": "no tooltip (visual knob estimate only)",
              "fx.dimension.mix": "no tooltip (visual knob estimate only)", "arp.velocity.target": "no tooltip (visual only)"}
NO_TOOLTIP_PREFIX = {"filter1.": "numeric knobs showed no tooltip in the compact panel (3 tries); expanded view not found",
                     "filter2.": "numeric knobs showed no tooltip in the compact panel (3 tries); expanded view not found"}
NOT_LOCATED = {"mixer.%s.filter_balance" % m: "not located on the MIX page (icon under each strip is the Env1 routing toggle)"
               for m in ("osc_a", "osc_b", "osc_c", "noise", "sub")}
SESSION2_NOTE = ("kFM_OSC is contextual: OSC A shows 'FM (B)', OSC B/C show 'FM (A)'. The session table's 'warp_var2 50 %' column is "
                 "attributed to warp_amount2 (kParamWarp2 = 0.5 was the only 0.5 warp leaf written in that preset).")


def readability(aid):
    if aid in NOT_LOCATED:
        return {"class": "NOT_LOCATED", "note": NOT_LOCATED[aid]}
    if aid in NO_TOOLTIP:
        return {"class": "NO_TOOLTIP", "note": NO_TOOLTIP[aid]}
    for pre, note in NO_TOOLTIP_PREFIX.items():
        if aid.startswith(pre) and not aid.endswith((".type", ".enabled")):
            return {"class": "NO_TOOLTIP", "note": note}
    return {"class": "UNKNOWN_OR_READABLE", "note": "no scan note says otherwise; tooltip availability not mapped yet"}


def J(p):
    return json.load(open(p))


# ------------------------------------------------------------------------------------------------ UI view model ------
def view_of(aid):
    """(page, view) where a control is read. INFERRED from Serum 2's module layout and the scan notes: no layout
    screenshots were available, so these are the unit of the pass-count estimate, not measured facts."""
    m = aid.split(".")
    mod = m[0]
    if re.fullmatch(r"osc[ABC]", mod):
        return "OSC", "OSC_" + mod[-1]
    if mod == "oscNoise":
        return "OSC", "NOISE"
    if mod == "sub":
        return "OSC", "SUB"
    if re.fullmatch(r"filter[12]", mod):
        return "OSC", "FILTER" + mod[-1]
    if re.fullmatch(r"env\d", mod):
        return "OSC", "ENV" + mod[-1]
    if re.fullmatch(r"lfo\d", mod):
        return "OSC", "LFO" + mod[3:]
    if re.fullmatch(r"macro\d", mod):
        return "BOTTOM", "MACROS"
    if mod == "mixer":
        return "MIX", "MIX"
    if mod == "fx":
        return "FX", "FX_" + m[1]
    if mod == "arp":
        return "ARP", "ARP"
    if mod == "voice":
        return "BOTTOM", "VOICING"
    if mod == "global":
        return "GLOBAL", "GLOBAL"
    return "OTHER", mod.upper()


FX_TYPE_OF_CTX = {c: c[3:] for c in FX_CONTEXTS_ORDER}


# ------------------------------------------------------------------------------------------------ host crosswalk -----
HOST_PREFIX = [(r"^osc([ABC])\.", r"{0} "), (r"^oscNoise\.", "Noise "), (r"^sub\.", "Sub "), (r"^filter([12])\.", "Filter {0} "),
               (r"^env(\d)\.", "Env {0} "), (r"^lfo(\d)\.", "LFO {0} "), (r"^macro(\d)\.", "Macro {0}"),
               (r"^mixer\.([abc])\.", "{0}>"), (r"^mixer\.noise\.", "Noise>"), (r"^mixer\.sub\.", "Sub Osc>"),
               (r"^mixer\.filter([12])\.", "Filter {0}>")]
ALIAS_WORDS = {"semitone": "semi", "fine": "fine", "detune": "uni detune", "sample_loop_start": "loop start", "sample_loop_end": "loop end",
               "sample_loop_crossfade": "loop x-fade", "warp_amount": "warp", "warp_mode": "warp mode", "warp_amount2": "warp 2",
               "warp_mode2": "warp 2 mode", "warp_var2": "warp 2 var", "enabled": "on", "enable": "enable", "resonance": "res",
               "cutoff": "freq", "bus1": "bus1", "bus2": "bus2", "filter_balance": "filter balance", "level": "level"}


def tokens(s):
    return set(t for t in re.split(r"[^a-z0-9]+", s.lower()) if t)


def name_candidates(aid, host):
    """Heuristic host candidates for a control: module prefix filter + token overlap of the field name."""
    field = aid.split(".")[-1]
    for pat, fmt in HOST_PREFIX:
        m = re.match(pat, aid)
        if m:
            pre = fmt.format(*[g.upper() if len(g) == 1 and g.isalpha() else g for g in m.groups()])
            break
    else:
        return []
    want = tokens(ALIAS_WORDS.get(field, field.replace("_", " ")))
    out = []
    for name, h in host.items():
        if not name.startswith(pre):
            continue
        rest = tokens(name[len(pre):])
        if not rest:
            score = 0.5 if pre.startswith("Macro") else 0
        else:
            score = len(want & rest) / len(want | rest)
        if score > 0:
            out.append((round(score, 2), name, h["index"]))
    return sorted(out, key=lambda x: (-x[0], x[2]))


def crosswalk(aid, rec, host, ctx):
    causal_names, texts = set(), {}
    for v in (rec or {}).get("values", []):
        if v.get("probe") or v.get("load_error"):
            continue
        changed = v.get("host_params_changed") or []
        causal_names |= set(changed)
        t = (v.get("gui_mutated") or {}).get("host_text_display") or {}
        if t:
            texts[json.dumps(v["written"])] = t
    idx = {n: host[n]["index"] for n in causal_names if n in host}
    if aid.startswith("fx."):
        return {"host_identity": None, "confidence": "NONE", "method": "none",
                "reason": "Serum exposes FX only as generic 'FX Main Param 1-16' / 'FX Bus n Param 1-16' slots; the per-FX binding "
                          "of a slot is not established by any evidence", "ambiguous_with": [], "value_texts": texts}
    if len(causal_names) == 1:
        n = next(iter(causal_names))
        return {"host_identity": {"name": n, "index": idx.get(n)}, "confidence": "HIGH", "method": "causal_single_host_param_changed",
                "ambiguous_with": [], "value_texts": texts}
    if len(causal_names) > 1:
        heur = [c[1] for c in name_candidates(aid, host)]
        best = next((n for n in heur if n in causal_names), sorted(causal_names)[0])
        return {"host_identity": {"name": best, "index": idx.get(best)}, "confidence": "MEDIUM",
                "method": "causal_multi_param_resolved_by_name" if best in heur else "causal_multi_param_unresolved",
                "ambiguous_with": sorted((n, idx.get(n)) for n in causal_names if n != best), "value_texts": texts,
                "note": "host_params_changed is capped at 8 names per value in bulk_engine; the set may be truncated"
                        if len(causal_names) >= 8 else None}
    cand = name_candidates(aid, host)
    if cand:
        top = cand[0]
        tie = [c for c in cand[1:] if c[0] == top[0]]
        return {"host_identity": {"name": top[1], "index": top[2]}, "confidence": "LOW" if not tie else "AMBIGUOUS",
                "method": "name_heuristic_only (no host text changed when written in the campaign)", "score": top[0],
                "ambiguous_with": [(c[1], c[2]) for c in cand[1:4]], "value_texts": texts}
    return {"host_identity": None, "confidence": "NONE", "method": "none",
            "reason": "no host parameter changed when written and no name candidate in the module", "ambiguous_with": [], "value_texts": texts}


# ------------------------------------------------------------------------------------------------ fingerprints -------
def golden(k):
    return 0.15 + 0.70 * ((k * PHI + 0.5) % 1.0)


def nice(x, lo, hi, kind):
    span = hi - lo
    if kind == "log":
        mag = 10 ** math.floor(math.log10(abs(x))) if x else 1
        return round(x / mag * 10) / 10 * mag    # 2 significant digits
    step = 0.01 if span <= 2 else (0.1 if span <= 20 else 1.0)
    return round(round(x / step) * step, 6)


def retained_values(rec):
    out = []
    for v in (rec or {}).get("values", []):
        if v.get("load_error") or v.get("state_value") is None:
            continue
        out.append((v["written"], v["state_value"], v.get("probe", False)))
    return out


NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def display_hints(aid, rec, ui_obs):
    """From host texts of the campaign (B tier, used only to CHOOSE values, never as verification) and earlier screen
    readings: integer_display, and the effective range where the display still changes (saturation trimmed)."""
    pts = []
    for v in (rec or {}).get("values", []):
        if v.get("probe") or v.get("load_error"):
            continue
        t = list(((v.get("gui_mutated") or {}).get("host_text_display") or {}).values())
        m = NUM.search(t[0]) if len(t) == 1 else None
        if m and isinstance(v["written"], (int, float)):
            pts.append((float(v["written"]), float(m.group()), t[0].strip()))
    pts.sort()
    hint = {"integer_display": False, "eff_lo": None, "eff_hi": None, "texts": pts}
    if pts:
        # integer rounding of the RAW value only when the display IS the raw value (e.g. octave -2 -> '-2'); a scaled
        # integer display (warp 0.25 -> '25') keeps fine raw steps
        hint["integer_display"] = all(re.fullmatch(r"[-+]?\d+", t.split()[0] if t.split() else t) for _w, _n, t in pts) and \
            all(abs(w - n) < 1e-6 for w, n, _t in pts if not (hint_sat(pts, w)))
        hint["curve"] = fit_curve(pts)
        if len(pts) >= 2 and pts[-1][1] == pts[-2][1]:           # saturates at the top: last change happens at pts[k]
            k = len(pts) - 1
            while k > 0 and pts[k - 1][1] == pts[-1][1]:
                k -= 1
            hint["eff_hi"] = pts[k][0]
        if len(pts) >= 2 and pts[0][1] == pts[1][1]:
            k = 0
            while k < len(pts) - 1 and pts[k + 1][1] == pts[0][1]:
                k += 1
            hint["eff_lo"] = pts[k][0]
    if ui_obs and isinstance(ui_obs.get("expected_target"), float) and ui_obs.get("screen_displayed"):
        m = NUM.search(str(ui_obs["screen_displayed"]))
        t = float(ui_obs["expected_target"])
        if m and t % 1 and re.fullmatch(r"[-+]?\d+", m.group()) and abs(float(m.group()) - t) <= 0.5:   # e.g. 3.5 shown as 4
            hint["integer_display"] = True
    if ui_obs and isinstance(ui_obs.get("expected_target"), (int, float)) and ui_obs.get("screen_displayed") is not None \
            and not NUM.search(str(ui_obs["screen_displayed"])):
        hint["eff_hi"] = float(ui_obs["expected_target"]) / 10.0      # screen showed a word (e.g. 'Limit') at that target: saturated
        hint["saturated_on_screen_at"] = ui_obs["expected_target"]
    return hint


def hint_sat(pts, w):
    """True if w lies in a saturated tail (its display equals a neighbour's): excluded from the identity test."""
    ns = [n for ww, n, _t in pts]
    i = [ww for ww, _n, _t in pts].index(w)
    return (i > 0 and ns[i] == ns[i - 1]) or (i < len(ns) - 1 and ns[i] == ns[i + 1])


def fit_curve(pts):
    """Cheap model check over host-text points (B tier; a hypothesis for DIRECT_UI to confirm, never a verdict):
    identity, linear scale k*x, square k*x^2, dB of x^2 (40*log10 x). Returns the model name that fits all points."""
    good = [(w, n) for w, n, _t in pts if w > 0]
    if len(good) < 2:
        return None
    tests = {"identity": lambda w: w, "percent_linear": lambda w: 100 * w, "percent_square": lambda w: 100 * w * w,
             "db_square": lambda w: 40 * math.log10(w)}
    for name, f in tests.items():
        if all(abs(f(w) - n) <= max(0.051, 0.02 * abs(n), 0.5 if float(n).is_integer() else 0) for w, n in good):   # integer displays round
            return name
    return None


def predict(curve, v):
    if curve is None or not isinstance(v, (int, float)) or (v <= 0 and curve == "db_square"):
        return None
    return {"identity": lambda: v, "percent_linear": lambda: 100 * v, "percent_square": lambda: 100 * v * v,
            "db_square": lambda: 40 * math.log10(v)}[curve]()


class Alloc:
    """Per-preset allocator: one golden-ratio counter and one enum rotation for the whole preset, so sibling controls
    (env1-4, lfo1-6, osc A/B/C) and controls sharing a view never receive the same value."""

    def __init__(self):
        self.k = 0
        self.used_enum = defaultdict(list)
        self.family_vals = defaultdict(set)     # field name -> numeric values already used (siblings)
        self.view_vals = defaultdict(set)       # view -> numeric values already used
        self.all_vals = set()                   # every numeric value in the whole preset: globally unique fingerprints
        self.shown = defaultdict(set)           # page -> numbers expected on screen (raw, predicted display, percentage)
        self.page = None
        self.page_words = defaultdict(set)      # page -> enum words already shown (no same label twice on one page)

    def pick_word(self, words, forbid, vocab_key):
        used = self.used_enum[vocab_key]
        free = [w for w in words if json.dumps(w) not in forbid]
        on_page = self.page_words[self.page]
        pick = next((w for w in free if w not in used and str(w).lower() not in on_page), None) or \
            next((w for w in free if w not in used), None)
        if pick is None:                          # vocabulary exhausted: reuse least recently used
            pick = min(free or words, key=lambda w: used.index(w) if w in used else -1)
        used.append(pick)
        on_page.add(str(pick).lower())
        return pick

    def numeric(self, aid, d, base, forbid, hint, view):
        kind = d["kind"]
        lo, hi = float(d["min"]), float(d["max"])
        if hint["eff_hi"] is not None:
            hi = min(hi, hint["eff_hi"])
        if hint["eff_lo"] is not None:
            lo = max(lo, hint["eff_lo"])
        fam = aid.split(".")[-1]
        integer = kind == "int" or hint["integer_display"]
        for attempt in range(900):
            f = golden(self.k)
            self.k += 1
            refine = 10 ** (attempt // 300)          # 1, 10, 100: finer display steps only once coarser ones run out
            if kind == "log":
                v = nice(lo * (hi / lo) ** f, lo, hi, kind)
                if refine > 1:
                    v = float("%.*g" % (1 + len(str(refine)), lo * (hi / lo) ** f))
            else:
                v = lo + f * (hi - lo)
                if integer:
                    v = float(round(v))
                else:
                    span = hi - lo
                    step = (0.01 if span <= 2 else (0.1 if span <= 20 else 1.0)) / refine
                    v = round(round(v / step) * step, 6)
            v = min(max(v, lo), hi)
            if json.dumps(v) in forbid or (base is not None and not isinstance(base, str) and close(base, v)):
                continue
            if v in self.family_vals[fam] or v in self.view_vals[view] or self.taken(v, lo, hi, hint):
                continue
            break
        else:
            v = None
            if integer:                              # integer display: nearest unused whole number in [lo+1, hi-1]
                target = lo + golden(self.k) * (hi - lo)
                pool = [float(x) for x in range(int(math.ceil(lo)) + 1, int(math.floor(hi)))]
                pool = [x for x in pool if not self.taken(x, lo, hi, hint) and x not in self.family_vals[fam]
                        and json.dumps(x) not in forbid and not (base is not None and not isinstance(base, str) and close(base, x))]
                if pool:
                    v = min(pool, key=lambda x: abs(x - target))
            if v is None:
                raise AssertionError("no globally unique value left for %s in [%s, %s]" % (aid, lo, hi))
        self.family_vals[fam].add(v)
        self.view_vals[view].add(v)
        self.all_vals.add(v)
        self.shown[self.page].update(self.display_keys(v, lo, hi, hint))
        return v

    @staticmethod
    def display_keys(v, lo, hi, hint):
        """Numbers a human could see for value v: the host-text model's prediction (display precision), the raw value,
        and for 0..1 controls the percentage. A value is only free if none of these is already on screen elsewhere."""
        keys = {round(v, 2)}
        pr = predict(hint.get("curve"), v)
        if pr is not None:
            keys.add(round(pr, 1 if abs(pr) < 10 else 0))
        if lo == 0.0 and hi == 1.0:
            keys.add(round(100 * v, 0))
        return keys

    def taken(self, v, lo, hi, hint):
        return v in self.all_vals or bool(self.display_keys(v, lo, hi, hint) & self.shown[self.page])


def allocate(ctrls, recs, params, base_for, avoid, A, ui_by, view):
    out = {}
    A.page = view.split("/")[0]
    for aid in ctrls:
        p = params[aid]
        d = p["domain"]
        kind = d["kind"]
        base = base_for(aid)
        rec = recs.get(aid)
        forbid = {json.dumps(base)} | {json.dumps(x) for x in (avoid.get(aid) or [])}
        if p["mutation"]["kind"] == "leaf_set":
            words = [w for w in d["values"] if p["mutation"]["table"].get(w)]         # empty table entry == writes nothing (default)
            out[aid] = A.pick_word(words, forbid, json.dumps(sorted(words)))
        elif kind in ("enum_str", "enum"):
            kept = {json.dumps(w) for w, s, pr in retained_values(rec) if not pr and w == s}
            words = [w for w in d["values"] if not rec or json.dumps(w) in kept] or list(d["values"])
            out[aid] = A.pick_word(words, forbid, json.dumps(sorted(map(str, d["values"]))))
        elif kind == "bool":
            out[aid] = 0.0 if base in (1.0, True) else 1.0
        elif kind == "text":
            out[aid] = "FP_" + aid.replace(".", "_").upper()[:14]
        elif kind == "open":       # Serum's own stored values (after its clamping) are the executable ones
            stored = sorted({s for w, s, pr in retained_values(rec) if isinstance(s, (int, float)) and not isinstance(s, bool)})
            cands = [s for s in stored if json.dumps(s) not in forbid and not (base is not None and close(base, s))]
            fresh = [s for s in cands if s not in A.all_vals] or [s for s in cands if s not in A.view_vals[view]]
            pick = (fresh or cands)
            out[aid] = pick[len(pick) // 2] if pick else None
            if out[aid] is not None:
                A.view_vals[view].add(out[aid])
                A.all_vals.add(out[aid])
        else:
            out[aid] = A.numeric(aid, d, base, forbid, display_hints(aid, rec, ui_by.get(aid)), view)
    return out


# ------------------------------------------------------------------------------------------------ structural bases ---
def fx_units(types):
    return [FxUnitSpec(type=t, params={}, wet=100.0) for t in types]


def base_wavetable():
    """INIT (all oscillators in WAVETABLE mode, the init default) + all 12 FX units in the giant's slot order."""
    return apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": fx_units([FX_TYPE_OF_CTX[c] for c in FX_CONTEXTS_ORDER])}))


def base_sample(fx_types):
    """INIT + OSC A/B/C switched to SAMPLE with the giant preset's own sample reference (the file your Serum already
    loads), loop mode kept (loop points need it); nothing else from the giant is carried."""
    body = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": fx_units(fx_types)}))
    g = unpack_file(os.path.join(GV, "VERIFY_REFERENCE_FULL.SerumPreset")).data
    for i in range(3):
        o = body["Oscillator%d" % i]
        gp = g["Oscillator%d" % i]["plainParams"]
        o["plainParams"] = {k: gp[k] for k in ("kParamType", "kParamLoopMode") if k in gp}
        s = copy.deepcopy(g["Oscillator%d" % i]["SampleOsc%d" % i])
        s["plainParams"] = {k: v for k, v in s["plainParams"].items() if k == "kParamWarpMenu"}
        o["SampleOsc%d" % i] = s
    return body


def fx_path(path, slot):
    return [path[0], "FX", slot] + list(path[3:])


# ------------------------------------------------------------------------------------------------ main ---------------
def main():
    os.makedirs(OUT, exist_ok=True)
    acct = J(os.path.join(ED, "campaign_accounting_v1.json"))
    man = J(os.path.join(HERE, "manifest_campaign_v1.json"))
    params = {p["atlas_id"]: p for p in man["parameters"]}
    led = {e["atlas_id"]: e for e in J(os.path.join(ED, "closure_ledger_v3.json"))["candidates"]}
    plan = {c["atlas_id"]: c for c in J(os.path.join(GV, "giant_verification_plan.json"))["candidates"]}
    recs = {r["atlas_id"]: r for r in J(os.path.join(ED, "campaign_run_gui_v1.json"))["records"]}
    bt = J(BT)["controls"]
    host_dump = J(os.path.join(GV, "reference_parameter_text.json"))
    host = host_dump["reference"]
    all_ids = [c["atlas_id"] for c in acct["candidates"]]
    ui_by = {o["atlas_id"]: o for o in J(os.path.join(ED, "direct_ui_evidence_v2.json"))["observations"]}
    assert len(all_ids) == len(set(all_ids)) == 330

    # ---------------- alias groups (controls sharing one raw path in one context): one value, one reading
    by_path = defaultdict(list)
    for a, p in params.items():
        by_path[(p["context"], json.dumps(resolve_path(p["mutation"])))].append(a)
    alias_of = {}
    for grp in by_path.values():
        grp = sorted(grp)
        for a in grp[1:]:
            alias_of[a] = grp[0]

    # ---------------- workload
    work, residual = [], {}
    for a in all_ids:
        ui = led[a]["direct_ui_evidence"]["status"]
        if a not in params:
            residual[a] = "NOT_DERIVED: raw stored vocabulary unknown, so no valid raw value can be written"
            continue
        if a == "global.use_ultra_on_render":
            residual[a] = "Serum never stored any written value for this key in the campaign (STATE_NOT_OBSERVED): no preset can carry it"
            continue
        if ui == "UI_CONFIRMED" and a not in ANCHORS:
            continue
        if a in alias_of and alias_of[a] in params:
            continue                         # verified through its alias-group representative
        work.append(a)

    # ---------------- engine-mode requirement per control
    def engine(a):
        p = resolve_path(params[a]["mutation"])
        if params[a]["context"] == "OSC_SAMPLE":
            return "SAMPLE"
        if len(p) > 1 and str(p[1]).startswith("WTOsc"):
            return "WAVETABLE"
        return None

    def slot(a):
        p = resolve_path(params[a]["mutation"])
        return p[0] if str(p[0]).startswith("Oscillator") else None

    # ---------------- conflict graph + DSatur colouring
    lfo_shape_test = {a for a in work if re.fullmatch(r"lfo\d\.shape", a)}
    lfo_mode_test = {a for a in work if re.fullmatch(r"lfo\d\.mode", a)}
    edges = defaultdict(set)
    reasons = {}
    for a in work:
        for b in work:
            if a >= b:
                continue
            why = None
            if engine(a) and engine(b) and engine(a) != engine(b) and slot(a) == slot(b):
                why = "%s needs %s mode, %s needs %s mode on the same oscillator slot %s" % (a, engine(a), b, engine(b), slot(a))
            elif a in lfo_shape_test and b in lfo_mode_test and a.split(".")[0] == b.split(".")[0]:
                why = "%s (shape test) and %s (mode=Envelope test) on the same LFO: shape/mode coupling" % (a, b)
            elif b in lfo_shape_test and a in lfo_mode_test and a.split(".")[0] == b.split(".")[0]:
                why = "%s (shape test) and %s (mode=Envelope test) on the same LFO: shape/mode coupling" % (b, a)
            if why:
                edges[a].add(b)
                edges[b].add(a)
                reasons[(a, b)] = why
    # 2-colouring: SAMPLE-engine controls and LFO shape tests in colour 1; everything else (WAVETABLE controls, LFO
    # mode=Envelope tests, and every edge-free control) in colour 0, the preset that also carries the LFO 7 reference.
    # Asserted to be a PROPER colouring of the conflict graph; the graph contains an edge, so 2 is also the lower bound.
    colour = {a: 1 if (engine(a) == "SAMPLE" or a in lfo_shape_test) else 0 for a in work}
    assert all(colour[a] != colour[b] for a in work for b in edges[a]), "partition is not a proper colouring"
    n_presets = max(colour.values()) + 1
    clique_lb = 2 if any(edges.values()) else 1
    presets = defaultdict(list)
    for a in work:
        presets[colour[a]].append(a)

    # ---------------- calibration riders: second curve/vocabulary points ride in the mandatory second load
    riders = []
    if n_presets >= 2:
        for a in ("fx.compressor.attack", "fx.compressor.gain", "fx.compressor.ratio", "fx.compressor.thresh", "fx.reverb.type"):
            if a in params and colour.get(a) == 0:
                riders.append(a)

    names = {0: "BULK_01_WAVETABLE_MAIN", 1: "BULK_02_SAMPLE_CALIBRATION"}
    idx_presets, cmap_assign = [], defaultdict(list)
    fx_slot = {FX_TYPE_OF_CTX[c]: i for i, c in enumerate(FX_CONTEXTS_ORDER)}
    for pi in range(n_presets):
        members = sorted(presets[pi]) + (sorted(riders) if pi == 1 else [])
        needs_sample = any(engine(a) == "SAMPLE" for a in members)
        if pi == 0:
            base = base_wavetable()
            slot_of = dict(fx_slot)
        else:
            types = sorted({FX_TYPE_OF_CTX[params[a]["context"]] for a in members if params[a]["context"] in FX_TYPE_OF_CTX},
                           key=lambda t: fx_slot[t])
            base = base_sample(types) if needs_sample else apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": fx_units(types)}))
            slot_of = {t: i for i, t in enumerate(types)}

        def raw_path(a):
            p = resolve_path(params[a]["mutation"])
            ctx = params[a]["context"]
            return fx_path(p, slot_of[FX_TYPE_OF_CTX[ctx]]) if ctx in FX_TYPE_OF_CTX else p

        def base_for(a):
            return body_get(base, raw_path(a))

        # anchors avoid their old giant target (a NEW curve/vocabulary point); riders avoid their first-preset value
        avoid = {a: ([plan.get(a, {}).get("target_value")] if a in ANCHORS else []) + [x["value"] for x in cmap_assign.get(a, [])]
                 for a in members}
        views = defaultdict(list)
        for a in members:
            views[view_of(a)].append(a)
        values = {}
        A = Alloc()
        # interleave siblings (env1..4, lfo1..6, osc A/B/C) so family members draw consecutive, well-separated fractions
        for v in sorted(views, key=lambda v: (v[0], re.sub(r"\d", "", v[1]), v[1])):
            values.update(allocate(sorted(views[v], key=lambda a: (a.split(".")[-1], a)), recs, params, base_for, avoid, A, ui_by, "/".join(v)))
        # LFO: in the main preset every lfoN.mode = Envelope under the default shape (compatible proof); the conflict
        # reference lives on LFO 7 (LFO6, outside the 330): shape RandomSH + mode Envelope.
        for a in members:
            if re.fullmatch(r"lfo\d\.mode", a):
                values[a] = "Envelope"
        body = copy.deepcopy(base)
        written = []
        # order: leaf_set controls first (warp_mode2 resets kParamWarp2), then scalars
        for a in sorted(members, key=lambda x: (params[x]["mutation"]["kind"] != "leaf_set", x)):
            v = values.get(a)
            if v is None:
                residual.setdefault(a, "no executable value: Serum stored no non-default value in the campaign")
                continue
            m = params[a]["mutation"]
            path = raw_path(a)
            lv = _leaves_for(m, v, path)
            if params[a]["context"] in FX_TYPE_OF_CTX:
                lv = [(fx_path(p, slot_of[FX_TYPE_OF_CTX[params[a]["context"]]]), x) for p, x in lv]
            for p, x in lv:
                body_set(body, p, x)
            h = display_hints(a, recs.get(a), ui_by.get(a)) if isinstance(v, (int, float)) and not isinstance(v, bool) else {}
            pr = predict(h.get("curve"), v)
            written.append({"predicted_display": ({"value": round(pr, 2), "model": h["curve"], "tier": "B_host_text_model (hypothesis)"}
                                                  if pr is not None else None),
                            "atlas_id": a, "aliases": sorted(b for b, r in alias_of.items() if r == a), "value": v,
                            "raw_path": path, "leaves": [[p, x] for p, x in lv], "baseline_value": base_for(a),
                            "view": "/".join(view_of(a)), "gui_readability": readability(a), "role": "calibration_rider" if (pi == 1 and a in riders) else "verify",
                            "anchor": a in ANCHORS})
        extra = []
        if pi == 0:
            ref = [(["LFO6", "plainParams", "kParamType"], "RandomSH"), (["LFO6", "plainParams", "kParamMode"], "Envelope")]
            for p, x in ref:
                body_set(body, p, x)
            extra.append({"reference": "LFO7_CONTEXT_CONFLICT", "leaves": [[p, x] for p, x in ref],
                          "expect": "LFO 7: shape S&H, ENVELOPE greyed and FREE lit (native constraint); not one of the 330"})
        name = names.get(pi, "BULK_%02d" % (pi + 1))
        fpath = os.path.join(OUT, name + ".SerumPreset")
        pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=name), data=body), fpath)
        with open(fpath, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        man_p = {"preset": name + ".SerumPreset", "sha256": sha, "engine_mode_osc_ABC": "SAMPLE" if (pi and needs_sample) else "WAVETABLE",
                 "fx_rack_slots": {str(i): t for t, i in sorted(slot_of.items(), key=lambda x: x[1])},
                 "controls": written, "references": extra, "views": sorted({w["view"] for w in written})}
        idx_presets.append({"name": name, "file": name + ".SerumPreset", "n_controls": len(written),
                            "n_controls_incl_aliases": sum(1 + len(w["aliases"]) for w in written), "views": man_p["views"],
                            "_base": base, "_body": body, "_written": written, "_extra": extra, "_man": man_p})
        for w in written:
            for a in [w["atlas_id"]] + w["aliases"]:
                cmap_assign[a].append({"preset": name, "value": w["value"], "role": w["role"], "view": w["view"]})

    # ---------------- validation (pure, before anything is reported)
    checks = {}
    for P in idx_presets:
        back = unpack_file(os.path.join(OUT, P["file"])).data
        assert back == pack_unpack(BASE.metadata, P["_body"]), "roundtrip mismatch " + P["name"]
        intended = {json.dumps(p) for w in P["_written"] for p, _ in w["leaves"]} | {json.dumps(p) for e in P["_extra"] for p, _ in e["leaves"]}
        changed = {json.dumps(p) for p, _a, _b in diff_leaves(pack_unpack(BASE.metadata, P["_base"]), back)}
        unintended = changed - intended
        assert not unintended, "%s: unintended leaves %s" % (P["name"], sorted(unintended)[:5])
        final = {}                        # last writer wins (warp_mode2's side leaf kParamWarp2 is then set by warp_amount2)
        for w in P["_written"]:
            for p, x in w["leaves"]:
                final[json.dumps(p)] = (x, w["atlas_id"])
        for w in P["_written"]:
            for p, x in w["leaves"]:
                fx, owner = final[json.dumps(p)]
                if owner != w["atlas_id"]:
                    w.setdefault("superseded_side_leaves", []).append({"leaf": p, "wrote": x, "then_set_by": owner, "final": fx})
                got = body_get(back, p)
                assert got == fx or (isinstance(fx, float) and close(got, fx)), "%s %s leaf %s: expected %r got %r" % (P["name"], owner, p, fx, got)
        # fingerprints: (1) numeric values unique within a view; (2) sibling controls of one field family (env1-4.sustain,
        # lfo1-6.rate, oscA/B/C.x) unique across views, numeric AND enum (enum only while the vocabulary has room);
        # (3) no value equal to the baseline; (4) a calibration rider never repeats its first-preset value.
        coll = []
        byview, fam = defaultdict(list), defaultdict(list)
        for w in P["_written"]:
            kind = params[w["atlas_id"]]["domain"]["kind"]
            if kind in ("bool", "text", "open"):
                continue
            fam[(w["atlas_id"].split(".")[-1], json.dumps(sorted(map(str, params[w["atlas_id"]]["domain"].get("values") or []))))].append(w)
            if isinstance(w["value"], (int, float)) and kind not in ("enum", "enum_str"):   # enums: identity + label, not value
                byview[w["view"]].append(w)
        for v, lst in byview.items():
            vals = [x["value"] for x in lst]
            dup = [x for x in set(vals) if vals.count(x) > 1]
            if dup:
                coll.append(("view", P["name"], v, sorted(dup)[:5]))
        for (f, vocab), lst in fam.items():
            vals = [json.dumps(x["value"]) for x in lst]
            room = len(json.loads(vocab)) if vocab != "[]" else 10 ** 9
            if len(set(vals)) < min(len(vals), room - 1 if room < 10 ** 9 else len(vals)):
                coll.append(("family", P["name"], f, sorted(vals)))
        allv = defaultdict(list)
        for w in P["_written"]:
            if params[w["atlas_id"]]["domain"]["kind"] in ("continuous", "signed", "log", "int"):
                allv[json.dumps(w["value"])].append(w["atlas_id"])
        dup_global = {v: a for v, a in allv.items() if len(a) > 1}
        if dup_global:
            coll.append(("global_numeric_duplicate", P["name"], dup_global))
        shared = defaultdict(list)                  # values that CANNOT be unique: stated, not hidden
        for w in P["_written"]:
            k = params[w["atlas_id"]]["domain"]["kind"]
            if k in ("bool", "enum", "enum_str", "open") or params[w["atlas_id"]]["mutation"]["kind"] == "leaf_set":
                shared[json.dumps(w["value"])].append(w["atlas_id"])
        P["_shared"] = {v: a for v, a in shared.items() if len(a) > 1}
        for w in P["_written"]:
            if w["baseline_value"] is not None and json.dumps(w["value"]) == json.dumps(w["baseline_value"]):
                coll.append(("equals_baseline", P["name"], w["atlas_id"]))
            if w["role"] == "calibration_rider":
                first = [x["value"] for x in cmap_assign[w["atlas_id"]] if x["preset"] != P["name"]]
                if any(json.dumps(x) == json.dumps(w["value"]) for x in first):
                    coll.append(("rider_repeats_first_value", w["atlas_id"], w["value"]))
        checks[P["name"]] = {"numeric_values_globally_unique": True,
                             "shared_values_by_necessity": {v: a for v, a in P["_shared"].items()},
                             "roundtrip": True, "unintended_leaves": 0, "all_leaves_landed": True, "fingerprint_collisions": coll}
        assert not coll, coll
        # domain validity
        for w in P["_written"]:
            d = params[w["atlas_id"]]["domain"]
            v = w["value"]
            if d["kind"] in ("continuous", "signed", "log", "int"):
                assert d["min"] <= v <= d["max"], (w["atlas_id"], v, d)
            if d["kind"] in ("enum_str", "enum", "text") and params[w["atlas_id"]]["mutation"]["kind"] != "leaf_set" and d["kind"] != "text":
                assert v in d["values"], (w["atlas_id"], v)

    for P in idx_presets:
        json.dump(P["_man"], open(os.path.join(OUT, P["name"] + ".controls.json"), "w"), indent=1, default=repr)

    # ---------------- 330 control map
    s2 = SESSION2
    entries = []
    for a in all_ids:
        ac = next(c for c in acct["candidates"] if c["atlas_id"] == a)
        L = led[a]
        p = params.get(a)
        rec = recs.get(a)
        cw = crosswalk(a, rec, host, p["context"] if p else None)
        hid = cw["host_identity"]
        ref_txt = host.get(hid["name"], {}).get("text") if hid else None
        init_txt = host_dump["init"].get(hid["name"], {}).get("text") if hid else None
        ui = L["direct_ui_evidence"]
        assigned = cmap_assign.get(a, [])
        if a in residual:
            nxt = "RESIDUAL: " + residual[a]
        elif assigned:
            nxt = "READ in " + ", ".join("%s (%s, value %r, view %s)" % (x["preset"], x["role"], x["value"], x["view"]) for x in assigned)
        else:
            nxt = "none: already DIRECT_UI confirmed"
        if ui["status"] == "UI_CONFIRMED" and a not in ANCHORS:
            closure = "UI_CONFIRMED"
        elif a in residual:
            closure = "RESIDUAL_" + ("NOT_DERIVED" if a not in params else "NOT_STORED")
        else:
            closure = "PENDING_BULK_UI_READ"
        entries.append({
            "atlas_id": a,
            "semantic_field": bt.get(a),
            "mutation_mechanism": p["mechanism"] if p else None,
            "raw_path": resolve_path(p["mutation"]) if p else None,
            "context_requirements": {"campaign_context": p["context"] if p else None,
                                     "engine_mode": (("SAMPLE" if p["context"] == "OSC_SAMPLE" else "WAVETABLE" if (len(resolve_path(p["mutation"])) > 1 and str(resolve_path(p["mutation"])[1]).startswith("WTOsc")) else None) if p else None),
                                     "coupling": ("lfo mode=Envelope is disabled while shape=S&H (native constraint)" if re.fullmatch(r"lfo\d\.(mode|shape)", a) else
                                                  "warp_mode2's leaf set resets kParamWarp2; write warp_mode2 before warp_amount2" if re.search(r"warp_(mode2|amount2)$", a) else None),
                                     "alias_of": alias_of.get(a), "aliases": sorted(b for b, r in alias_of.items() if r == a)},
            "declared_domain": p["domain"] if p else None,
            "serum_native_identity": {"host_parameter": hid, "confidence": cw["confidence"], "method": cw["method"],
                                      "ambiguous_with": cw["ambiguous_with"], "note": cw.get("reason") or cw.get("note")},
            "verification": {"assignments": assigned, "next_action": nxt},
            "evidence": {
                "A_causal": {"ledger_status": L["status"], "reason": L.get("reason"), "derived": ac["derived"],
                             "giant_plan_status": plan.get(a, {}).get("status"), "giant_target": plan.get(a, {}).get("target_value")},
                "B_host_text": {"campaign": L["host_text_evidence"],
                                "reference_dump": {"name": hid["name"], "index": hid["index"], "text_in_VERIFY_REFERENCE_FULL": ref_txt,
                                                   "text_in_init": init_txt} if hid else None,
                                "campaign_value_texts": cw["value_texts"] or None,
                                "is_direct_ui": False},
                "C_direct_ui": {"direct_ui_evidence_v2": ui,
                                "session2_supplementary": dict(s2[a], note=SESSION2_NOTE, source="d0f75df ui_scan_2026-09-26.md") if a in s2 else None},
            },
            "gui_readability": readability(a),
            "closure_classification": closure,
            "unresolved": (None if closure == "UI_CONFIRMED" else
                           "vocabulary/raw values unknown; needs GUI-set + file readback per label" if closure == "RESIDUAL_NOT_DERIVED" else
                           residual.get(a) if a in residual else
                           ("native display of the bulk value, then %s" % ("curve calibration against the earlier reading" if a in ANCHORS else "MATCH/MISMATCH verdict"))),
        })
    assert len(entries) == 330 and len({e["atlas_id"] for e in entries}) == 330
    json.dump({"version": 1, "total_controls": 330, "authorizes_nothing": True,
               "evidence_tiers": {"A_causal": "state readback/restoration/isolation/roundtrip (campaign + ledger)",
                                  "B_host_text": "VST3 host parameter text; never counts as DIRECT_UI",
                                  "C_direct_ui": "human-visible Serum GUI observation only"},
               "host_dump": {"file": "giant_verify_out/reference_parameter_text.json", "n_host_params": host_dump["n_host_params"],
                             "n_changed_from_init": len(host_dump["changed_from_init"]),
                             "caveat": "dump is keyed by name; duplicate host names (if any) were collapsed by the dump script. Indices are kept."},
               "closure_counts": dict(Counter(e["closure_classification"] for e in entries)),
               "host_confidence_counts": dict(Counter(e["serum_native_identity"]["confidence"] for e in entries)),
               "controls": entries}, open(MAP_OUT, "w"), indent=1, default=repr)

    # ---------------- index + report numbers
    for P in idx_presets:
        for k in ("_base", "_body", "_written", "_extra", "_man", "_shared"):
            P.pop(k)
    pages = defaultdict(set)
    for P in idx_presets:
        for v in P["views"]:
            pages[P["name"]].add(v)
    idx = {"generated_only": True, "rendered": False, "verified": False, "n_presets": n_presets, "lower_bound_presets": clique_lb,
           "presets": idx_presets, "conflict_edges": [{"a": a, "b": b, "why": w} for (a, b), w in sorted(reasons.items())],
           "residual": residual, "validation": checks,
           "work_controls": len(work), "isolation_corpus_loads": 1035}
    json.dump(idx, open(os.path.join(OUT, "index.json"), "w"), indent=1, default=repr)
    return idx, entries, work, residual, alias_of, reasons


def report(idx, entries, work, residual, alias_of, reasons):
    led = {e["atlas_id"]: e for e in J(os.path.join(ED, "closure_ledger_v3.json"))["candidates"]}
    C = lambda it: dict(sorted(Counter(it).items(), key=lambda x: -x[1]))
    status = C(e["status"] for e in led.values())
    host = C(e["host_text_evidence"]["status"] for e in led.values())
    ui = C(e["direct_ui_evidence"]["status"] for e in led.values())
    conf = C(e["serum_native_identity"]["confidence"] for e in entries)
    host_mapped_gui_unverified = sum(1 for e in entries if e["serum_native_identity"]["confidence"] in ("HIGH", "MEDIUM")
                                     and e["evidence"]["C_direct_ui"]["direct_ui_evidence_v2"]["status"] != "UI_CONFIRMED")
    s2 = sum(1 for e in entries if e["evidence"]["C_direct_ui"]["session2_supplementary"])
    mans = {P["name"]: J(os.path.join(OUT, P["name"] + ".controls.json")) for P in idx["presets"]}
    # page / sub-view passes (views inferred; FX scroll positions from the scan: 8 units visible, 4 below the fold)
    def passes(m):
        views = sorted({w["view"] for w in m["controls"]} | ({"OSC/LFO7"} if m["references"] else set()))
        pages = defaultdict(list)
        for v in views:
            pages[v.split("/")[0]].append(v.split("/")[1])
        n = 0
        rows = []
        for pg, vs in sorted(pages.items()):
            if pg == "OSC":
                tabs = sorted({x for x in vs if re.match(r"(ENV|LFO)\d", x)})
                k = 1 + len(tabs)           # the main OSC/filter view + one per ENV/LFO tab
            elif pg == "FX":
                slots = m["fx_rack_slots"]
                units = [slots[k] for k in sorted(slots, key=int)]
                k = 1 if len(units) <= 8 else 2
            else:
                k = 1
            n += k
            rows.append((pg, k, ", ".join(vs)))
        return n, rows
    hover = lambda m: sum(1 for w in m["controls"] if params_kind(w) not in ("bool", "enum_str", "enum", "text"))
    lines = []
    L = lines.append
    L("# Bulk DIRECT_UI verification: optimization report")
    L("")
    L("Generated by `build_bulk_ui_verification.py` from repository evidence only. Nothing was loaded into Serum, rendered or verified.")
    L("Page/tab structure is INFERRED from Serum's module layout and the scan notes, because no layout screenshots were available;")
    L("the preset count does not depend on it, only the pass estimate does.")
    L("")
    L("## 1. Accounting: 330 controls, each exactly once")
    L("")
    L("| layer | counts |")
    L("|---|---|")
    L("| A. causal (closure_ledger_v3 status) | %s |" % ", ".join("%s %d" % kv for kv in status.items()))
    L("| B. host text (campaign) | %s |" % ", ".join("%s %d" % kv for kv in host.items()))
    L("| C. DIRECT_UI (direct_ui_evidence_v2) | %s |" % ", ".join("%s %d" % kv for kv in ui.items()))
    L("| C. DIRECT_UI supplementary (session 2, recorded separately) | %d controls (warp on the WT secondary preset) |" % s2)
    L("| host identity crosswalk | %s |" % ", ".join("%s %d" % kv for kv in conf.items()))
    L("| host-mapped (HIGH/MEDIUM) but not GUI-confirmed | %d |" % host_mapped_gui_unverified)
    L("| alias pairs (one raw path, verified once) | %d: %s |" % (len(alias_of), ", ".join("%s=%s" % (b, a) for b, a in sorted(alias_of.items()))))
    L("")
    L("Closure after this build: %s." % ", ".join("%s %d" % kv for kv in C(e["closure_classification"] for e in entries).items()))
    L("")
    L("## 2. Genuinely unresolved -> new workload")
    L("")
    L("- Already DIRECT_UI-confirmed and not an anchor: **%d** (subtracted)." % sum(1 for e in entries if e["closure_classification"] == "UI_CONFIRMED"))
    L("- Verified through an alias partner: **%d**." % len(alias_of))
    L("- Cannot be put in any preset (residual): **%d**: %s." % (len(residual), "; ".join("`%s` (%s)" % kv for kv in sorted(residual.items()))))
    L("- Needs a bulk read: **%d** controls (representatives), anchors included deliberately." % len(work))
    L("")
    L("## 3. The batching problem and its solution")
    L("")
    L("Conflict graph over the %d work controls. The ONLY hard edges the evidence establishes:" % len(work))
    L("")
    L("1. **Oscillator engine mode** (%d edges): WTOsc controls (warp_*, wavetable) need WAVETABLE and SampleOsc controls need SAMPLE on the same slot." % sum(1 for w in reasons.values() if "mode on the same oscillator" in w))
    L("2. **LFO shape/mode coupling** (%d edges): mode=Envelope is disabled under S&H (proven twice on screen). Whether chaotic shapes (Rossler/Lorenz/Path) also disable Envelope is unknown, so a shape test and a mode=Envelope test never share an LFO." % sum(1 for w in reasons.values() if "shape/mode" in w))
    L("")
    L("Everything else (all 12 FX units in one rack, 4 envelopes, 6 LFOs, both filters, mixer, ARP, global, voicing, macros) has no edge: the giant preset already proved the 12-unit rack and all sections load together.")
    L("")
    L("**Result: %d presets. Lower bound: %d** (the graph has an edge, so one preset is impossible). The partition is asserted to be a proper colouring, so **2 is optimal**." % (idx["n_presets"], idx["lower_bound_presets"]))
    L("")
    L("| preset | controls (+aliases) | osc engine | FX rack | structural reason |")
    L("|---|---|---|---|---|")
    why = {"BULK_01_WAVETABLE_MAIN": "all WAVETABLE controls + every LFO mode=Envelope test under the default shape + every edge-free control; carries the LFO 7 conflict reference",
           "BULK_02_SAMPLE_CALIBRATION": "the SAMPLE-mode controls (A/B/C loop crossfade) + LFO shape tests (split from mode tests) + second calibration points riding the mandatory second load"}
    for P in idx["presets"]:
        m = mans[P["name"]]
        L("| `%s` | %d (+%d) | %s | %s | %s |" % (P["name"], P["n_controls"], P["n_controls_incl_aliases"] - P["n_controls"], m["engine_mode_osc_ABC"],
                                               ", ".join(m["fx_rack_slots"].values()), why.get(P["name"], "")))
    L("")
    L("## 4. Fingerprints (how each value was chosen)")
    L("")
    L("- Continuous: golden-ratio sequence over the safe interior 15-85% of the range (log domains in log space), rounded to display steps. One counter runs across the whole preset, so sibling controls (env1-4, lfo1-6, osc A/B/C) never share a value; the validation checks that per view and per field family.")
    L("- The safe range is shrunk where the campaign's host texts show Serum saturating (for example `global.transpose` shows -24 for -48 and -24, and `bend_range_up` stays 24 above 24). It is also shrunk where the screen already showed a word instead of a number (compressor ratio 'Limit' at 31622, so the new points are 430 and 210).")
    L("- Integer rounding is used only when the display equals the raw value (octave, semitone). Scaled integer displays such as warp '25' for 0.25 keep fine raw steps.")
    L("- Enums rotate through non-default words per vocabulary across the whole preset (for example warp mode A/B/C = sync/PWM/bend; reverb Hall in BULK_01 and Space in BULK_02, where Space is one of the schema words missing from Serum). Booleans flip. Macro names are self-identifying text.")
    L("- **Uniqueness rule**: every numeric raw value is unique across the WHOLE preset. Every expected on-screen number (the raw value, the host-text model prediction, and the percentage for 0-1 controls) is unique within its page. Enum labels are not repeated on a page while the vocabulary has another option. A strict all-pages display uniqueness is impossible: more than 99 controls display a 0-100 integer or percentage, and only 99 whole numbers fit strictly inside that range.")
    for P in idx["presets"]:
        sh = {k: v for k, v in idx["validation"][P["name"]]["shared_values_by_necessity"].items()}
        if sh:
            L("- Shared by necessity in `%s` (identified by control identity and position, not value): %s." % (P["name"], "; ".join(
                "%s x%d (%s)" % (k, len(v), "booleans" if k in ("1.0", "0.0") and len(v) > 5 else ", ".join(v)) for k, v in sorted(sh.items()))))
    L("  Open-range controls can only use values Serum itself stored, so a few coincide across pages. The six LFO modes are 'Envelope' by design, because that is the test.")
    L("- `predicted_display` in the manifests is a B-tier model fitted to the campaign host texts. It is a hypothesis for the screen read to confirm or refute, never a verdict.")
    L("")
    L("## 5. Calibration anchors (deliberately placed)")
    L("")
    rows = []
    for P in idx["presets"]:
        for w in mans[P["name"]]["controls"]:
            if w["anchor"]:
                pdx = w.get("predicted_display")
                rows.append("| `%s` | %s | %r | %s |" % (w["atlas_id"], P["name"], w["value"], ("%s (%s)" % (pdx["value"], pdx["model"])) if pdx else "-"))
    L("| control | preset | value | predicted display (B-tier hypothesis) |")
    L("|---|---|---|---|")
    lines.extend(sorted(rows))
    L("")
    L("- **Sustain** (host texts, B tier): Env 1 shows -24.1/-12.0/-5.0 dB and Env 2-4 show 6/25/56 % for raw 0.25/0.5/0.75. That is exactly display = raw², so the 'mismatch' is very likely a squared display curve, not a bad write. BULK_01's four sustains (0.54/0.17/0.24/0.57) predict -10.7 dB / 3 % / 6 % / 32 %: reading them on screen confirms or refutes the model in one pass.")
    L("- **LFO**: in BULK_01, LFO1-6 have mode=Envelope with the default shape (the compatible proof). LFO 7, which is outside the 330, has S&H + Envelope as the native-conflict reference, so the conflict and the compatible case are seen side by side in one load.")
    L("- **Warp**: BULK_01 keeps A/B/C in WAVETABLE with distinct warp modes and amounts. `warp_mode2` is written through its leaf set (raw `kFM_OSC`-style values, not the spec word `'fm'` the giant builder wrote), and then `warp_amount2` is written, because the leaf set resets `kParamWarp2`.")
    L("")
    L("## 6. Local screen work")
    L("")
    tot_pass = tot_hover = 0
    for P in idx["presets"]:
        m = mans[P["name"]]
        n, rows = passes(m)
        h = hover(m)
        tot_pass += n
        tot_hover += h
        L("**%s**: %d page/tab views, about %d numeric reads (hover unless shown directly)." % (P["name"], n, h))
        L("")
        for pg, k, vs in rows:
            L("- %s x%d: %s" % (pg, k, vs))
        L("")
    ro = Counter(e["gui_readability"]["class"] for e in entries if e["closure_classification"] == "PENDING_BULK_UI_READ")
    L("Readability limits known from the scans: %s. Filter numeric knobs are the biggest block, and they need the filter's expanded view to be found; the `mixer.*.filter_balance` controls need locating first." % ", ".join("%s %d" % kv for kv in ro.items()))
    L("")
    L("## 7. Residual local workload (exact)")
    L("")
    L("1. Load `BULK_01_WAVETABLE_MAIN` and read its views; load `BULK_02_SAMPLE_CALIBRATION` and read its views: **2 loads, %d views, about %d numeric reads**." % (tot_pass, tot_hover))
    L("2. `arp.transpose.shape`: 18 display labels are known; the raw strings are not. Set each label in the GUI, save, and read the file back: **18 save/readbacks** (or fewer if the raw strings turn out to equal `arp.pattern.shape`'s, which one save of 'Up' would indicate).")
    L("3. `global.voice_priority`: enumerate its menu labels, then one save/readback per label.")
    L("4. `global.use_ultra_on_render`: toggle it in the GUI, save, and read the file (1 op). Serum never stored a written value, so a preset cannot set it.")
    nl = sorted(e["atlas_id"] for e in entries if e["gui_readability"]["class"] == "NOT_LOCATED" and e["closure_classification"] == "PENDING_BULK_UI_READ")
    L("5. Locate the filter-balance control on screen for %s (%d pending controls), 1 search." % (", ".join("`%s`" % a for a in nl), len(nl)))
    L("6. Reserve only: the 1,035 isolation presets and the per-control BISECT files, for a control whose bulk reading is ambiguous.")
    L("")
    L("## 8. Why this is close to the minimum")
    L("")
    L("- **Loads**: 2 is the proven lower bound. Each oscillator slot must be seen in WAVETABLE and in SAMPLE mode, and a slot has one mode per preset. Any 1-preset plan leaves either %d SAMPLE or %d WAVETABLE controls unverifiable." % (sum(1 for a in work if params_engine(a) == "SAMPLE"), sum(1 for a in work if params_engine(a) == "WAVETABLE")))
    L("- **Views**: every view in BULK_02 is forced by a control that cannot be in BULK_01: the SAMPLE osc view, the LFO shape tabs and the FX view (FX only because the second compressor/reverb point rides a view that the second load already needs; dropping it saves 1 view but loses the second curve point for 4 anchors). BULK_01's views are one per UI region that holds unverified controls; no region is visited twice.")
    L("- **Compared with the isolation corpus**: 1,035 loads, each followed by at least 1 view, versus 2 loads and %d views: **%.0fx fewer loads** and about %.0fx fewer views." % (tot_pass, 1035 / 2, 1035 / max(tot_pass, 1)))
    L("- **What stays unminimised**: page passes assume the inferred layout. With the layout screenshots the pass count can be tightened (for example if ENV/LFO tabs share a view), but the preset count cannot go below 2.")
    L("")
    L("## 9. Validation (run by the builder; any failure aborts the build)")
    L("")
    for k, v in idx["validation"].items():
        L("- `%s`: repacked file == intended body (roundtrip), 0 unintended leaves vs its structural base, every intended leaf landed (last writer wins, superseded side leaves recorded), numeric raw values globally unique, displays unique per page, 0 fingerprint collisions (view / sibling family / baseline / rider)." % k)
    L("- Every value lies inside its declared domain (and inside Serum's observed effective range where known); enum values are vocabulary members; leaf-set words come from the manifest table.")
    L("- 330 entries in `serum_full_control_map_v1.json`, unique. Existing evidence files are read-only inputs: only new files are written.")
    L("- Tiers stay separate: `B_host_text.is_direct_ui` is false everywhere, and session-2 readings live in `C_direct_ui.session2_supplementary`, not merged into `direct_ui_evidence_v2`.")
    open(os.path.join(OUT, "OPTIMIZATION_REPORT.md"), "w").write("\n".join(lines) + "\n")


_PARAMS = None


def params_engine(a):
    params_kind({"atlas_id": a})
    p = _PARAMS[a]
    path = resolve_path(p["mutation"])
    return "SAMPLE" if p["context"] == "OSC_SAMPLE" else ("WAVETABLE" if len(path) > 1 and str(path[1]).startswith("WTOsc") else None)


def params_kind(w):
    global _PARAMS
    if _PARAMS is None:
        _PARAMS = {p["atlas_id"]: p for p in J(os.path.join(HERE, "manifest_campaign_v1.json"))["parameters"]}
    return _PARAMS[w["atlas_id"]]["domain"]["kind"]


if __name__ == "__main__":
    idx, entries, work, residual, alias_of, reasons = main()
    report(idx, entries, work, residual, alias_of, reasons)
    print(json.dumps({k: idx[k] for k in ("n_presets", "lower_bound_presets", "work_controls")}))
    for P in idx["presets"]:
        print(P["name"], P["n_controls"], P["n_controls_incl_aliases"], P["views"])
    print("residual", residual)
    print(Counter(e["closure_classification"] for e in entries), Counter(e["serum_native_identity"]["confidence"] for e in entries))
