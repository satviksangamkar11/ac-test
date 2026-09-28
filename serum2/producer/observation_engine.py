"""Unified Observation Engine — converts raw evidence into validated candidates.

One abstraction for all observation modalities:
  - TEXT (literal transcription)
  - ENUM (resolve to canonical vocabulary)
  - NUMERIC (syntactic parsing + unit parsing; semantic validation deferred to state_ledger)
  - ENABLE_STATE (checkbox/visual state)
  - ROUTE_TEXT (modulation source/destination)
  - GRAPH_DERIVED (shapes known to be derived from stored fields; Phase 1 schema)
  - RUNTIME_STATE (explicitly excluded from preset reproduction)
  - SLIDER_PIXEL (interface only; currently unsupported)

Each strategy normalizes raw evidence into a candidate with explicit outcome:
  - CANDIDATE: ready for state_ledger.derive() validation
  - NOT_APPLICABLE: runtime/transient state; cannot become preset observation
  - UNSUPPORTED_MODALITY: modality exists but not yet implemented
  - IDENTITY_UNRESOLVED: observation metadata unclear or missing

Qwen output remains UNTRUSTED_CANDIDATE. No VLM output becomes terminal
observation without deterministic validation by state_ledger._coerce().
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
import re


# Outcome types for observation candidates
OUTCOME_CANDIDATE = "CANDIDATE"  # Ready for state_ledger validation
OUTCOME_NOT_APPLICABLE = "NOT_APPLICABLE"  # Runtime/transient state; not preset evidence
OUTCOME_UNSUPPORTED_MODALITY = "UNSUPPORTED_MODALITY"  # Modality not yet implemented
OUTCOME_IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"  # Observation metadata unclear


@dataclass
class ObservationCandidate:
    """Result of an observation strategy; input to state_ledger.derive()."""
    control_id: str
    raw_value: Any
    normalized_value: Any
    strategy: str  # TEXT, ENUM, NUMERIC, ENABLE_STATE, ROUTE_TEXT, GRAPH_DERIVED, RUNTIME_STATE, SLIDER_PIXEL
    confidence: float  # 0.0-1.0
    outcome: str = OUTCOME_CANDIDATE  # CANDIDATE, NOT_APPLICABLE, UNSUPPORTED_MODALITY, IDENTITY_UNRESOLVED
    evidence_hash: Optional[str] = None  # crop SHA256 or frame hash if available
    modality_notes: str = ""
    vlm_source: bool = False  # True if this came from Qwen, False if deterministic extraction


class ObservationStrategy(ABC):
    """Base class for observation strategies."""

    @abstractmethod
    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        """Normalize raw value into a candidate.

        context may include:
          - control_id, control_type, element_kind
          - enum_values: list of valid enum options (for ENUM strategy)
          - unit: unit string (for NUMERIC strategy)
          - roi_hash, frame_hash: evidence provenance
          - vlm_source: True if value came from Qwen
        """
        pass


class TextObservationStrategy(ObservationStrategy):
    """Raw text transcription — minimal normalization, maximum fidelity."""

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()
        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=s,
            strategy="TEXT",
            confidence=1.0 if s else 0.0,
            outcome=OUTCOME_CANDIDATE,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            vlm_source=context.get("vlm_source", False),
        )


class EnumObservationStrategy(ObservationStrategy):
    """Enum/selector value — resolve to canonical domain entry.

    Handles Qwen output format like "Chaos: Lorenz" by extracting after the colon.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()
        domain = context.get("enum_values", [])

        # Handle Qwen prefix format: "Chaos: Lorenz" → extract "Lorenz"
        if ":" in s:
            parts = s.split(":", 1)
            s = parts[1].strip()

        if not s:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=None,
                strategy="ENUM",
                confidence=0.0,
                outcome=OUTCOME_CANDIDATE,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                modality_notes="empty enum value",
                vlm_source=context.get("vlm_source", False),
            )

        # Exact match first
        if s in domain:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=s,
                strategy="ENUM",
                confidence=1.0,
                outcome=OUTCOME_CANDIDATE,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                vlm_source=context.get("vlm_source", False),
            )

        # Case-insensitive exact match
        norm_s = s.lower()
        for d in domain:
            if d.lower() == norm_s:
                return ObservationCandidate(
                    control_id=context.get("control_id", ""),
                    raw_value=raw_value,
                    normalized_value=d,
                    strategy="ENUM",
                    confidence=0.95,
                    outcome=OUTCOME_CANDIDATE,
                    evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                    modality_notes=f"case-normalized {s} -> {d}",
                    vlm_source=context.get("vlm_source", False),
                )

        # No match
        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="ENUM",
            confidence=0.0,
            outcome=OUTCOME_CANDIDATE,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"enum {s} not in domain {domain}",
            vlm_source=context.get("vlm_source", False),
        )


class NumericObservationStrategy(ObservationStrategy):
    """Numeric value with optional unit — syntactic parsing only.

    This strategy parses number + unit from raw value. Handles Qwen output format
    like "VALUE=7" or "DRIVE=1.9" by extracting after the = prefix.
    Semantic validation (unit conversion, range clamping) remains in state_ledger._coerce().
    """

    _NUM_PATTERN = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(ms|s|hz|khz|db|%|:1)?\s*$", re.I)

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()

        # Handle Qwen prefix format: "VALUE=7", "DRIVE=1.9", etc.
        if "=" in s:
            parts = s.split("=", 1)
            s = parts[1].strip()

        m = self._NUM_PATTERN.match(s)

        if not m:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=None,
                strategy="NUMERIC",
                confidence=0.0,
                outcome=OUTCOME_CANDIDATE,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                modality_notes=f"non-numeric value: {s}",
                vlm_source=context.get("vlm_source", False),
            )

        num = float(m.group(1))
        unit = (m.group(2) or (context.get("unit") or "")).lower()

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=(num, unit),
            strategy="NUMERIC",
            confidence=1.0,
            outcome=OUTCOME_CANDIDATE,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            vlm_source=context.get("vlm_source", False),
        )


class EnableStateObservationStrategy(ObservationStrategy):
    """Checkbox/toggle state — visual classification.

    Handles Qwen output format like "STATE=OFF" by extracting after the = prefix.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()

        # Handle Qwen prefix format: "STATE=ON", "STATE=OFF", etc.
        if "=" in s:
            parts = s.split("=", 1)
            s = parts[1].strip()

        s_lower = s.lower()

        if s_lower in ("on", "true", "checked", "enabled"):
            result = "ON"
            conf = 1.0
        elif s_lower in ("off", "false", "unchecked", "disabled"):
            result = "OFF"
            conf = 1.0
        else:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=None,
                strategy="ENABLE_STATE",
                confidence=0.0,
                outcome=OUTCOME_CANDIDATE,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                modality_notes=f"unrecognized enable/disable state: {s}",
                vlm_source=context.get("vlm_source", False),
            )

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=result,
            strategy="ENABLE_STATE",
            confidence=conf,
            outcome=OUTCOME_CANDIDATE,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            vlm_source=context.get("vlm_source", False),
        )


class RouteTextObservationStrategy(ObservationStrategy):
    """Modulation route source/destination — text validation.

    Handles Qwen output format like "SOURCE=Env 2\nDESTINATION=Filter 1 Freq".
    Parsing of SOURCE/DESTINATION pairs is deferred to state_ledger; normalized_value is None.
    Raw value preserved for ledger to extract key=value pairs.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()
        route_type = context.get("route_element", "")  # "source" or "destination"

        # ROUTE_TEXT preserves raw value for ledger parsing; no normalized_value
        # (parsing of KEY=VALUE pairs deferred to state_ledger)
        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="ROUTE_TEXT",
            confidence=1.0 if s else 0.0,
            outcome=OUTCOME_CANDIDATE,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"route {route_type} (raw text preserved for ledger parsing)",
            vlm_source=context.get("vlm_source", False),
        )


class GraphDerivedObservationStrategy(ObservationStrategy):
    """Graph/curve shapes classified as non-independent visual evidence.

    Phase 1 schema closure identified stored source fields:
      - LFO Chaos: kParamType enum determines curve type
      - OSC waveforms: wavetable name + wt_position determine shape

    These source fields are retained. The rendering derivation is not claimed as fully
    proven. Mark as NOT_APPLICABLE since visual shapes are not independent preset
    parameters; they derive from stored fields or runtime animation.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        graph_type = context.get("graph_type", "")  # "lorenz_curve", "waveform_shape", etc.
        source_fields = context.get("derived_from", [])  # list of source field names

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="GRAPH_DERIVED",
            confidence=1.0,
            outcome=OUTCOME_NOT_APPLICABLE,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"visual evidence ({graph_type}) from source fields {source_fields}; not independent preset parameter; Phase 2 classifies as non-independent",
            vlm_source=False,
        )


class RuntimeStateObservationStrategy(ObservationStrategy):
    """Runtime/transient state — explicitly excluded from preset reproduction.

    Example: voice-count meter (0/8) is live playhead state, not a stored parameter.
    These get outcome NOT_APPLICABLE; they cannot flow into state_ledger.derive().
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        runtime_type = context.get("runtime_type", "")  # "voice_meter", "level_meter", etc.

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="RUNTIME_STATE",
            outcome=OUTCOME_NOT_APPLICABLE,
            confidence=1.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"runtime/transient state ({runtime_type}); must not be treated as preset parameter",
            vlm_source=False,
        )


class SliderPixelObservationStrategy(ObservationStrategy):
    """Slider pixel-position calibration — interface only; not yet implemented.

    This strategy is reserved for Matrix Amount and similar pixel-position-to-value
    conversions. Currently always returns outcome UNSUPPORTED_MODALITY to indicate
    the modality exists but implementation is Phase 3 work.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="SLIDER_PIXEL",
            outcome=OUTCOME_UNSUPPORTED_MODALITY,
            confidence=0.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes="slider pixel calibration not implemented yet (Phase 3)",
            vlm_source=context.get("vlm_source", False),
        )


# Strategy registry
_STRATEGIES: Dict[str, ObservationStrategy] = {
    "TEXT": TextObservationStrategy(),
    "ENUM": EnumObservationStrategy(),
    "NUMERIC": NumericObservationStrategy(),
    "ENABLE_STATE": EnableStateObservationStrategy(),
    "ROUTE_TEXT": RouteTextObservationStrategy(),
    "GRAPH_DERIVED": GraphDerivedObservationStrategy(),
    "RUNTIME_STATE": RuntimeStateObservationStrategy(),
    "SLIDER_PIXEL": SliderPixelObservationStrategy(),
}


def get_strategy(strategy_name: str) -> ObservationStrategy:
    """Get a strategy by name."""
    if strategy_name not in _STRATEGIES:
        raise ValueError(f"Unknown observation strategy: {strategy_name}")
    return _STRATEGIES[strategy_name]


class ObservationEngine:
    """Main entry point for observation normalization.

    Takes a raw observation and context, selects the appropriate strategy,
    and returns a candidate with explicit outcome.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        """Select strategy and normalize observation.

        context keys:
          - control_id (required)
          - element_kind: one of CONTROL, SELECTOR, TEXT_IDENTITY, ENABLE_STATE, ROUTE, TOPOLOGY, GRAPH, CURVE, REGION
          - control_type: "continuous", "enum", "toggle", "topology", "module_identity", "route"
          - enum_values: list of valid enum options (for ENUM strategy)
          - unit: unit string (for NUMERIC strategy)
          - roi_hash, frame_hash: evidence provenance
          - vlm_source: True if value came from Qwen
        """
        control_id = context.get("control_id", "")
        element_kind = context.get("element_kind")
        control_type = context.get("control_type")

        # Select strategy based on element_kind first, fall back to control_type
        strategy_name = self._select_strategy(element_kind, control_type, context)
        strategy = get_strategy(strategy_name)

        return strategy.observe(raw_value, context)

    def _select_strategy(self, element_kind: Optional[str], control_type: Optional[str], context: Dict[str, Any]) -> str:
        """Determine which strategy to use based on control metadata.

        Raises ValueError if metadata is ambiguous or insufficient.
        """

        # Explicit strategy requests
        if context.get("force_strategy"):
            return context["force_strategy"]

        # Element kind has priority (more specific)
        if element_kind == "ENABLE_STATE":
            return "ENABLE_STATE"
        elif element_kind == "TEXT_IDENTITY":
            return "TEXT"
        elif element_kind == "SELECTOR":
            return "ENUM"
        elif element_kind == "CONTROL":
            return "NUMERIC"
        elif element_kind == "ROUTE":
            return "ROUTE_TEXT"
        elif element_kind in ("GRAPH", "CURVE"):
            return "GRAPH_DERIVED"

        # Fall back to control_type
        if control_type == "enum":
            return "ENUM"
        elif control_type == "toggle":
            return "ENABLE_STATE"
        elif control_type == "continuous":
            return "NUMERIC"
        elif control_type == "route":
            return "ROUTE_TEXT"

        # No safe default: refuse silently-interpreted unknown metadata
        raise ValueError(
            f"Observation metadata insufficient or ambiguous: element_kind={element_kind}, control_type={control_type}. "
            f"Refusing to default to TEXT for unclassified observation. Outcome: IDENTITY_UNRESOLVED"
        )

    def adjudicated_observe(self, sources: List[Dict], context: Dict[str, Any], *, numeric_tol: float = 1e-3) -> "ObservationCandidate":
        """Wrap observe() with the multi-source adjudication policy.

        sources: list of dicts, each with at least {"raw_value": ..., "source": "<label>"} and
        optionally "confidence" overrides. Each entry is independently run through observe(),
        then the results are adjudicated via observation_policy.adjudicate().

        Returns an observation_policy.ObservationCandidate (not the engine's own ObservationCandidate)
        so the caller can distinguish OBSERVED / AMBIGUOUS / UNREADABLE outcomes without importing
        the policy module directly.
        """
        from serum2.producer.observation_policy import (
            ObservationCandidate as PolicyCandidate, OUTCOME_CANDIDATE, adjudicate,
        )
        policy_candidates = []
        for s in sources:
            raw = s.get("raw_value")
            src_label = s.get("source", "unknown")
            try:
                result = self.observe(raw, dict(context, **{k: v for k, v in s.items() if k not in ("raw_value", "source")}))
            except Exception as exc:
                policy_candidates.append(PolicyCandidate(
                    outcome="UNREADABLE", source=src_label, detail="observe() raised: %s" % exc))
                continue
            policy_candidates.append(PolicyCandidate(
                outcome=OUTCOME_CANDIDATE if result.outcome == OUTCOME_CANDIDATE else "UNREADABLE",
                value=result.normalized_value,
                confidence=s.get("confidence", result.confidence),
                source=src_label,
                control_id=result.control_id,
                evidence_hash=result.evidence_hash,
            ))
        return adjudicate(
            policy_candidates,
            numeric_tol=numeric_tol,
            requested_control_id=context.get("control_id", ""),
        )

    def observe_control_in_frame(self, frame_path: str, control_id: str) -> "ObservationCandidate":
        """Run real local VLM (+ OCR corroboration on the same ROI) against one frame image
        for one control, and return the adjudicated result.

        Generic candidate-selection mechanism (locate -> crop -> transcribe -> explicit null),
        adapted from the earlier roi_crop_extractor.py prototype in this repo: ask the VLM to
        LOCATE the control's bounding box on the full frame first, then crop to that ROI and
        ask it to transcribe ONLY the visible value there, replying UNREADABLE rather than
        guessing on occlusion/illegibility/wrong-context. This works for any control_id without
        a precomputed per-control pixel region. A small fast-path registry
        (_GENERIC_SERUM_UI_CROPS, fractions of frame size derived from Serum 2's own fixed
        OSC-page layout) skips the locate step for the 2 controls already validated this way,
        as an optimization, not a requirement -- every other control_id goes through locate.
        """
        from serum2.producer.observation_policy import ObservationCandidate as PolicyCandidate
        from serum2.producer.expected_inventory import resolve_observation_type
        import hashlib

        # Real per-control strategy from the Atlas -- never hardcoded to NUMERIC/CONTROL.
        # An Atlas-unresolvable control_id is explicit UNREADABLE, never a guessed strategy.
        _obs_kind, strategy = resolve_observation_type(control_id)
        if strategy is None:
            return PolicyCandidate(outcome="UNREADABLE", control_id=control_id,
                                    detail="control_id not resolvable in Atlas; no observation strategy")

        try:
            from PIL import Image
        except Exception as exc:
            return PolicyCandidate(outcome="UNREADABLE", control_id=control_id, detail="PIL unavailable: %s" % exc)

        try:
            im = Image.open(frame_path)
        except Exception as exc:
            return PolicyCandidate(outcome="UNREADABLE", control_id=control_id, detail="cannot open frame: %s" % exc)

        w, h = im.size
        crop_spec = _GENERIC_SERUM_UI_CROPS.get(control_id)
        field_index = field_count = None

        if crop_spec is not None:
            fx0, fy0, fx1, fy1, field_index, field_count = crop_spec
            box = (int(fx0 * w), int(fy0 * h), int(fx1 * w), int(fy1 * h))
        else:
            box = _locate_control_bbox(frame_path, control_id, (w, h))
            if box is None:
                return PolicyCandidate(outcome="UNREADABLE", control_id=control_id,
                                        detail="VLM locate step could not find control %r in this frame" % control_id)

        crop = im.crop(box)
        import io
        buf = io.BytesIO()
        crop.convert("RGB").save(buf, format="PNG")
        roi_hash = hashlib.sha256(buf.getvalue()).hexdigest()
        crop_path = frame_path + f".__roi_{control_id.replace('.', '_')}.png"
        crop.convert("RGB").save(crop_path)

        if crop_spec is not None:
            vlm_text, vlm_conf = _run_vlm_on_crop(crop_path, control_id, field_index, field_count, strategy=strategy)
        else:
            vlm_text, vlm_conf = _transcribe_roi(crop_path, control_id, strategy=strategy)
            if vlm_text is None:
                return PolicyCandidate(outcome="UNREADABLE", control_id=control_id,
                                        detail="VLM transcribe step returned UNREADABLE for %r" % control_id,
                                        evidence_hash=roi_hash)

        sources = [{"raw_value": vlm_text, "source": "qwen2.5-vl-3b-instruct", "confidence": vlm_conf}]

        # OCR corroboration is a numeric-fragment reader only -- meaningless for ENUM/
        # ENABLE_STATE/TEXT labels, so it is skipped for any non-NUMERIC strategy rather
        # than fed a value it cannot actually validate.
        if strategy == "NUMERIC":
            ocr_num, ocr_conf = _run_ocr_on_crop(crop_path, field_index, field_count) if crop_spec is not None \
                else _run_ocr_freeform(crop_path)
            if ocr_num is not None:
                sources.append({"raw_value": ocr_num, "source": "easyocr-1.7.2", "confidence": ocr_conf})

        context = {"control_id": control_id, "force_strategy": strategy, "roi_hash": roi_hash}
        if strategy == "ENUM":
            from serum2.reference.serum_atlas import get_control, normalize_control, EXACT, ALIAS
            resolution = normalize_control(control_id)
            control = get_control(resolution.canonical_id) if resolution.status in (EXACT, ALIAS) else None
            context["enum_values"] = list(getattr(control, "enum_values", None) or [])
        return self.adjudicated_observe(sources, context, numeric_tol=1e-3)

    def observe_frame_all_controls(self, frame_path: str) -> List[Dict[str, Any]]:
        """Evidence-first VLM census: identify all visible Serum controls without a target hint.

        Args:
            frame_path: Path to the full frame image (not a crop).

        Returns:
            List of dicts, each with keys: {"panel", "label", "value", "confidence", "evidence_hash"}

        The VLM prompt asks what controls are visible WITHOUT giving any control_id hint.
        This is used by the universal frame observer (Stage 5) to discover controls
        rather than search for pre-selected ones.
        """
        try:
            from PIL import Image
        except Exception:
            return []

        try:
            im = Image.open(frame_path)
        except Exception:
            return []

        import hashlib
        import io
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="PNG")
        frame_hash = hashlib.sha256(buf.getvalue()).hexdigest()

        import torch
        from qwen_vl_utils import process_vision_info
        model, proc = _load_vlm()

        # Generic evidence-first prompt: no control_id hint, just ask what's readable.
        # Two things confirmed empirically necessary on this 4-bit quantized 3B model:
        #  1. An example line -- without one the model defaults to a refusal even on
        #     frames with plainly legible text.
        #  2. NOT offering an explicit "say NO_READABLE_CONTROLS if unsure" escape hatch
        #     -- offering it made the model take it far more often than warranted, even
        #     right after it had just correctly transcribed the same crop under a
        #     differently-worded prompt. This discovery pass is not authoritative (see
        #     _adjudicate()'s docstring: its claimed VALUEs are discarded and re-verified
        #     per-control via the confidence-gated ROI crop in Stage 7), and the regex
        #     parse below already yields zero findings on any output with no matching
        #     lines, so no explicit fallback instruction is needed here.
        # Wording matters a great deal to this specific 3B model -- even innocuous-looking
        # placeholder elaboration ("<section name>" instead of "<section>") flipped it from
        # a reliable structured answer to emitting a single newline and stopping. Keep this
        # exact phrasing; it is the one empirically confirmed (repeatedly) to work.
        prompt = (
            "This is a screenshot of a music synthesizer plugin UI. "
            "List every parameter label and its current value that you can read. "
            "Format each as: PANEL: <section> CTRL: <label> VALUE: <value> CONF: <0.0-1.0>\n"
            "Example: PANEL: OSC A CTRL: OCT VALUE: -3 CONF: 0.9\n"
            "List as many as you can find."
        )

        msgs = [{"role": "user", "content": [{"type": "image", "image": frame_path}, {"type": "text", "text": prompt}]}]
        text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        img_objs, vids = process_vision_info(msgs)
        inp = proc(text=[text], images=img_objs, videos=vids, padding=True, return_tensors="pt").to(model.device)
        # NOTE: output_scores=True/return_dict_in_generate=True must NOT be passed here.
        # Confirmed empirically on this 4-bit quantized model: requesting per-step scores
        # changes the actual greedy-decoded text (same prompt+image, only this flag
        # differing, reliably flips the output between a real structured answer and the
        # NO_READABLE_CONTROLS refusal). The per-line confidence used below comes from the
        # model's own "CONF: <value>" text, not from these scores, so nothing is lost.
        out = model.generate(**inp, max_new_tokens=256, do_sample=False)
        gen = out[0][inp.input_ids.shape[1]:]
        result = proc.batch_decode([gen], skip_special_tokens=True)[0]

        if "NO_READABLE_CONTROLS" in result.upper():
            return []

        # Parse output lines matching: PANEL: <panel> CTRL: <label> VALUE: <value> CONF: <confidence>
        findings = []
        pattern = r"PANEL:\s*(.+?)\s+CTRL:\s*(.+?)\s+VALUE:\s*(.+?)\s+CONF:\s*([\d.]+)"
        for match in re.finditer(pattern, result, re.IGNORECASE):
            panel, label, value, conf_str = match.groups()
            try:
                conf = float(conf_str)
            except ValueError:
                conf = 0.5
            findings.append({
                "panel": panel.strip(),
                "label": label.strip(),
                "value": value.strip(),
                "confidence": min(1.0, max(0.0, conf)),
                "evidence_hash": frame_hash,
            })
        return findings


# ---------------------------------------------------------------------------
# Generic Serum-UI-layout crop registry + lazy local-model runners
# (used by ObservationEngine.observe_control_in_frame)
# ---------------------------------------------------------------------------

# control_id -> (x0_frac, y0_frac, x1_frac, y1_frac, field_index_in_row, expected_field_count)
# Fractions derived from Serum 2's fixed OSC-page panel geometry at 1920x1080; the same
# panel layout applies regardless of which tutorial is being captured, provided the capture
# shows Serum's OSC page at a similar aspect ratio (16:9, plugin filling the frame).
_GENERIC_SERUM_UI_CROPS: Dict[str, tuple] = {
    "env1.decay":    (0.1875, 0.7639, 0.3958, 0.7917, 2, 5),   # ATK/HOLD/DEC/SUS/REL row
    # OCT/SEM/FIN/CRS row — full row bbox shared by all 4 siblings; field_index selects the target.
    # oscA.octave keeps None/None (validated working; VLM reads whole crop as single field).
    "oscA.octave":   (0.1224, 0.1944, 0.3177, 0.2176, None, None),
    "oscA.semitone": (0.1224, 0.1944, 0.3177, 0.2176, 1, 4),   # SEM
    "oscA.fine":     (0.1224, 0.1944, 0.3177, 0.2176, 2, 4),   # FIN
    "oscA.crs":      (0.1224, 0.1944, 0.3177, 0.2176, 3, 4),   # CRS
}

_vlm_singleton = None
_ocr_singleton = None


def _load_vlm():
    global _vlm_singleton
    if _vlm_singleton is None:
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "models/Qwen2.5-VL-3B-Instruct", quantization_config=q, device_map="auto")
        proc = AutoProcessor.from_pretrained("models/Qwen2.5-VL-3B-Instruct",
                                              min_pixels=64 * 28 * 28, max_pixels=1024 * 28 * 28)
        _vlm_singleton = (model, proc)
    return _vlm_singleton


_STRATEGY_READ_DESCRIPTION = {
    "NUMERIC": "exact displayed numeric value. Answer with only the number (and unit/sign if shown), nothing else",
    "ENUM": "exact displayed selection/label text. Answer with only that text, nothing else",
    "ENABLE_STATE": "on/off (enabled/disabled) state. Answer with only ON or OFF, nothing else",
    "TEXT": "exact displayed text. Answer with only that text, nothing else",
}


def _run_vlm_on_crop(crop_path: str, control_id: str, field_index: Optional[int], field_count: Optional[int],
                     strategy: str = "NUMERIC"):
    from qwen_vl_utils import process_vision_info
    model, proc = _load_vlm()
    read_what = _STRATEGY_READ_DESCRIPTION.get(strategy, _STRATEGY_READ_DESCRIPTION["NUMERIC"])
    if field_index is not None and field_count is not None:
        ordinal = ["first", "second", "third", "fourth", "fifth", "sixth"][field_index] if field_index < 6 else str(field_index + 1)
        prompt = ("This is a crop of a Serum 2 synthesizer UI row with %d fields side by side. "
                  "Read ONLY the %s field's %s (the field labelled for control '%s')."
                  % (field_count, ordinal, read_what, control_id))
    else:
        prompt = ("This is a crop of a Serum 2 synthesizer UI showing the control '%s'. "
                  "Read its %s." % (control_id, read_what))
    msgs = [{"role": "user", "content": [{"type": "image", "image": crop_path}, {"type": "text", "text": prompt}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    img_objs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=img_objs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    out = model.generate(**inp, max_new_tokens=16, do_sample=False)
    gen = out[0][inp.input_ids.shape[1]:]
    result = proc.batch_decode([gen], skip_special_tokens=True)[0]
    return result, 1.0


def _run_ocr_on_crop(crop_path: str, field_index: Optional[int], expected_field_count: Optional[int]):
    global _ocr_singleton
    if field_index is None:
        return None, None
    import easyocr
    if _ocr_singleton is None:
        _ocr_singleton = easyocr.Reader(["en"], gpu=True)
    detections = _ocr_singleton.readtext(crop_path, detail=1)
    if len(detections) != expected_field_count or field_index >= len(detections):
        return None, None  # fragment count doesn't match expected row shape -- refuse rather than guess
    raw = detections[field_index][1]
    conf = detections[field_index][2]
    m = re.search(r"[+-]?\d+(?:\.\d+)?", raw.replace(",", ".").replace("$", "s"))
    return (float(m.group(0)), conf) if m else (None, None)


def _locate_control_bbox(frame_path: str, control_id: str, frame_size: tuple):
    """Stage 1 of the generic locate->transcribe pattern: ask the VLM to find control_id's
    bounding box anywhere in the full frame. Returns a PIL-crop-ready (x0,y0,x1,y1) pixel
    box, or None if the VLM cannot locate it (explicit null, never a guessed default region).
    """
    from qwen_vl_utils import process_vision_info
    model, proc = _load_vlm()
    w, h = frame_size
    # Use the human-readable display name from the Atlas so Qwen can match the visible label
    # (e.g. "Cutoff" or "Uni Detune") rather than the internal API key ("filter1.cutoff").
    try:
        from serum2.reference.serum_atlas import get_control as _gc
        _ctrl = _gc(control_id)
        _label = (getattr(_ctrl, 'display_name', None) or control_id) if _ctrl else control_id
        _panel = getattr(_ctrl, 'panel', None) if _ctrl else None
    except Exception:
        _label, _panel = control_id, None
    human_label = ("%s (%s panel)" % (_label, _panel)) if _panel else _label
    prompt = (
        "This is a screenshot of a Serum 2 synthesizer plugin UI. Locate the control "
        "labelled '%s'. If visible, reply with exactly one line: "
        "bbox=[x1,y1,x2,y2] using pixel coordinates in a %dx%d image. "
        "If it is not visible in this frame, reply exactly: NOT_VISIBLE" % (human_label, w, h)
    )
    msgs = [{"role": "user", "content": [{"type": "image", "image": frame_path}, {"type": "text", "text": prompt}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    img_objs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=img_objs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    out = model.generate(**inp, max_new_tokens=32, do_sample=False)
    result = proc.batch_decode([o[len(i):] for i, o in zip(inp.input_ids, out)], skip_special_tokens=True)[0]
    m = re.search(r"\[?\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]?", result)
    if not m:
        return None
    x0, y0, x1, y1 = (int(v) for v in m.groups())
    # Pad slightly for label context, clamp to frame bounds, reject degenerate boxes.
    pad = 6
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    return (x0, y0, x1, y1)


def _transcribe_roi(crop_path: str, control_id: str, strategy: str = "NUMERIC"):
    """Stage 2 of the generic locate->transcribe pattern: read ONLY the value visible in an
    already-located ROI crop, with an explicit UNREADABLE reply path -- never a guess.
    Returns (text, mean_token_confidence) or (None, 0.0) if the VLM reports UNREADABLE.
    """
    from qwen_vl_utils import process_vision_info
    model, proc = _load_vlm()
    read_what = _STRATEGY_READ_DESCRIPTION.get(strategy, _STRATEGY_READ_DESCRIPTION["NUMERIC"])
    prompt = (
        "This is a cropped region of a Serum 2 UI, located as the control '%s'. "
        "Read ONLY its %s. If it is occluded, too small, blurry, or this crop does not "
        "actually show that control, reply exactly: UNREADABLE." % (control_id, read_what)
    )
    msgs = [{"role": "user", "content": [{"type": "image", "image": crop_path}, {"type": "text", "text": prompt}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    img_objs, vids = process_vision_info(msgs)
    inp = proc(text=[text], images=img_objs, videos=vids, padding=True, return_tensors="pt").to(model.device)
    out = model.generate(**inp, max_new_tokens=16, do_sample=False)
    gen = out[0][inp.input_ids.shape[1]:]
    mean_prob = 1.0
    result = proc.batch_decode([gen], skip_special_tokens=True)[0]
    if "UNREADABLE" in result.upper():
        return None, 0.0
    # NUMERIC is the only strategy that requires a digit to be present in the reply -- an
    # ENUM/ENABLE_STATE/TEXT reading is legitimately non-numeric (e.g. "Lorenz", "ON").
    if strategy == "NUMERIC" and not re.search(r"\d", result):
        return None, 0.0
    return result, mean_prob


def _run_ocr_freeform(crop_path: str):
    """OCR corroboration for a located (not fixed-row) ROI: take the single highest-confidence
    numeric fragment anywhere in the crop, or (None, None) if none parses. Looser than the
    fixed-row _run_ocr_on_crop (which requires an exact expected fragment count) because a
    located ROI's fragment count isn't known in advance -- still never guesses a value with
    no digits in it."""
    global _ocr_singleton
    import easyocr
    if _ocr_singleton is None:
        _ocr_singleton = easyocr.Reader(["en"], gpu=True)
    detections = _ocr_singleton.readtext(crop_path, detail=1)
    best = None
    for _, raw, conf in detections:
        m = re.search(r"[+-]?\d+(?:\.\d+)?", raw.replace(",", ".").replace("$", "s"))
        if m and (best is None or conf > best[1]):
            best = (float(m.group(0)), conf)
    return best if best else (None, None)
