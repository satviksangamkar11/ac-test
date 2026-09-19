"""VisualReasoner — boundary for visual interpretation.

This module is the sole entry point for visual inference. It uses a FIXED
model (claude-haiku-4-5-20251001). The model is NOT selectable by callers.

Authority invariants:
    - VisualReasoner NEVER calls serum-mcp
    - VisualReasoner NEVER calls Ableton MCP
    - VisualReasoner NEVER modifies admission, capability contracts, or authority
    - VisualReasoner produces observations and interpretations ONLY
    - model_metadata.provider_attestation is ALWAYS null (no cryptographic proof)

TWO-STAGE DESIGN (transcript-first correction):
    Stage A — observe_frames(): OBSERVED ONLY. Reads exact UI state per
        frame (a target's displayed value, if legible). Never asked "what
        happened" or "what does this mean" — only "what is visible".
    Stage B — infer_from_diffs(): INFERRED ONLY, and deterministic. Takes
        the before/after CanonicalStateDiff objects that Stage A's
        structured readings produce (see diff_observed_states()) and
        derives production meaning FROM THE DIFF — never from a fresh
        model call over the image, never from genre/title convention. The
        exact value in the resulting VisualInterpretation always traces
        back to a specific frame_hash via the diff, not to a model guess.

    reason() remains for backward compatibility (single-call combined
    observe+infer, the pre-correction behavior) but new callers should
    prefer observe_frames() -> diff_observed_states() -> infer_from_diffs().

The resulting VisualEvidenceBundle is passed to the ProducerBrain, which
converts the best interpretation into a UniversalProductionIntent (concept +
direction only, no magnitude) and routes it through the existing authority
chain. The exact magnitude travels separately, via
bundle.observed_canonical_states / bundle.canonical_diffs.
"""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from serum2.source.visual_evidence import (
    VisualEvidenceBundle,
    VisualModelMetadata,
    VisualObservation,
    VisualInterpretation,
    ObservedCanonicalState,
    CanonicalStateDiff,
)

# The visual model is fixed and not caller-configurable.
_VISUAL_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """\
You are a video frame analyst specializing in music production software.
Your task is to examine frames from a music production tutorial video and identify:

1. OBSERVED FACTS: What is literally visible in each frame — specific UI controls,
   knob positions, parameter values, waveform shapes, preset names, etc.
   Do NOT interpret what these mean; only describe what you can see.

2. INFERRED MEANINGS: Production technique interpretations that you derive from
   the observed facts. These must cite which observations support them.

Rules:
- Keep observed and inferred completely separate
- For observations: describe only what is visually present
- For inferences: explain the production meaning and name the concept
- If Serum 2 is not visible in a frame, say so clearly
- If a control is too small or blurry to read, say the confidence is low
- Do NOT fabricate parameter values you cannot see

Respond ONLY with valid JSON matching the schema provided in the user message.
"""

_USER_PROMPT_TEMPLATE = """\
Analyze the following {n_frames} video frame(s) from a Serum 2 tutorial.
For each frame, provide observations and inferences.

Respond with this exact JSON schema:
{{
  "frames": [
    {{
      "frame_id": "<frame_id from input>",
      "timestamp_sec": <float>,
      "serum_visible": <true|false>,
      "observations": [
        {{
          "observation_text": "<literal description of what is visible>",
          "observable_type": "<ui_control|parameter_value|waveform_display|automation_lane|preset_name|plugin_view|general>",
          "ui_element": "<element name or null>",
          "estimated_value": "<visual estimate with unit or null>",
          "confidence": <0.0-1.0>
        }}
      ],
      "inferences": [
        {{
          "interpretation_text": "<production meaning derived from observations>",
          "production_concept": "<filter-cutoff|envelope-release|envelope-attack|oscillator-volume|lfo-rate|etc>",
          "semantic_direction": "<increase|decrease|higher|lower|longer|shorter|brighter|darker>",
          "supporting_frame_ids": ["<frame_id>"],
          "production_action": "<specific actionable description>",
          "confidence": <0.0-1.0>
        }}
      ]
    }}
  ]
}}

Frame data follows as images with their frame_ids and timestamps.
"""


_OBSERVE_ONLY_SYSTEM_PROMPT = """\
You are a video frame analyst specializing in music production software.
Your ONLY task is to report what is literally visible in each frame.

Rules:
- Describe only what is visually present. Do NOT interpret what it means,
  why it might have changed, or what the producer is trying to achieve.
- If a specific control is named as the target, read its EXACT displayed
  value (the number/unit shown on screen, e.g. "220 ms", "34%", "1.2 kHz").
  If you cannot read it precisely, say so and give your best estimate with
  a low confidence rather than fabricating an exact figure.
- If Serum 2 is not visible in a frame, say so clearly.
- Do NOT propose a production concept, a direction (increase/decrease), or
  any narrative about intent. That is a separate step this response is not
  part of.

Respond ONLY with valid JSON matching the schema provided in the user message.
"""

_OBSERVE_ONLY_USER_PROMPT_TEMPLATE = """\
Analyze the following {n_frames} video frame(s) from a Serum 2 tutorial.
{target_instruction}
For each frame, report ONLY what is visible — no interpretation.

Respond with this exact JSON schema:
{{
  "frames": [
    {{
      "frame_id": "<frame_id from input>",
      "timestamp_sec": <float>,
      "serum_visible": <true|false>,
      "observations": [
        {{
          "observation_text": "<literal description of what is visible>",
          "observable_type": "<ui_control|parameter_value|waveform_display|automation_lane|preset_name|plugin_view|general>",
          "ui_element": "<element name or null>",
          "estimated_value": "<visual estimate with unit or null>",
          "confidence": <0.0-1.0>
        }}
      ],
      "target_reading": {{
        "target": "<the named target, or null if none was given>",
        "value": "<exact displayed value with unit, e.g. '220 ms', or null if not legible>",
        "confidence": <0.0-1.0>
      }},
      "unknown": ["<something you could not determine from this frame, e.g. 'exact UI gesture used to change the value', 'which secondary control this affects' — empty list if nothing is unclear>"]
    }}
  ]
}}

Frame data follows as images with their frame_ids and timestamps.
"""


def _numeric_with_unit(value_str: Optional[str]) -> Optional[Tuple[float, str]]:
    """Parse '220 ms' -> (220.0, 'ms'). Returns None if unparseable."""
    if not value_str:
        return None
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z%]+)\s*$", value_str.strip())
    if not m:
        return None
    try:
        return float(m.group(1)), m.group(2).lower()
    except ValueError:
        return None


# target name -> (increase_word, decrease_word) for deterministic direction
_TARGET_DIRECTION_WORDS: Dict[str, Tuple[str, str]] = {
    "Env1.Release": ("longer", "shorter"),
    "Env1.Attack": ("longer", "shorter"),
    "Filter.Cutoff": ("higher", "lower"),
    "Filter.Resonance": ("higher", "lower"),
}

# target name -> universal concept (matches producer_brain._INTENT_TO_CONCEPT)
_TARGET_TO_CONCEPT: Dict[str, str] = {
    "Env1.Release": "note-release",
    "Env1.Attack": "envelope-attack",
    "Filter.Cutoff": "filter-cutoff",
    "Filter.Resonance": "filter-cutoff",  # no separate resonance concept in the brain yet
}


def diff_observed_states(bundle: VisualEvidenceBundle) -> List[CanonicalStateDiff]:
    """Pure Python, deterministic: pair up bundle.observed_canonical_states
    by target (earliest timestamp = before, latest = after) and record
    whether the value actually changed.

    No model call. This is what makes the exact value traceable to frames
    rather than to an interpretation — the diff is computed the same way
    every time from the same structured readings.
    """
    by_target: Dict[str, List[ObservedCanonicalState]] = {}
    for state in bundle.observed_canonical_states:
        by_target.setdefault(state.target, []).append(state)

    diffs: List[CanonicalStateDiff] = []
    for target, states in by_target.items():
        if len(states) < 2:
            continue
        ordered = sorted(states, key=lambda s: s.timestamp_sec)
        before, after = ordered[0], ordered[-1]
        diffs.append(CanonicalStateDiff(
            target=target,
            before=before,
            after=after,
            changed=(before.value != after.value),
        ))
    return diffs


def infer_from_diffs(
    bundle: VisualEvidenceBundle,
    diffs: Optional[List[CanonicalStateDiff]] = None,
) -> VisualEvidenceBundle:
    """Stage B: deterministic INFERRED interpretations from before/after
    CanonicalStateDiff objects. No model call — the interpretation's exact
    value is always the diff's `after.value`, never a fresh model guess, so
    there is nothing here that can hallucinate a different number than what
    Stage A actually read off a frame.

    Produces one VisualInterpretation per changed diff, appended to
    bundle.interpretations and bundle.canonical_diffs.
    """
    diffs = diffs if diffs is not None else diff_observed_states(bundle)
    bundle.canonical_diffs = diffs

    for d in diffs:
        if not d.changed:
            continue
        concept = _TARGET_TO_CONCEPT.get(d.target)
        if concept is None:
            continue  # unmapped target — do not guess a concept

        before_num = _numeric_with_unit(d.before.value)
        after_num = _numeric_with_unit(d.after.value)
        inc_word, dec_word = _TARGET_DIRECTION_WORDS.get(d.target, ("higher", "lower"))
        if before_num and after_num and before_num[1] == after_num[1]:
            direction = inc_word if after_num[0] > before_num[0] else dec_word
        else:
            # Values present but not both cleanly numeric/same-unit — direction
            # genuinely unknown rather than guessed.
            direction = None

        if direction is None:
            continue

        interp = VisualInterpretation(
            interpretation_text=(
                "%s changed from %s (t=%.1fs) to %s (t=%.1fs), a %s change."
                % (d.target, d.before.value, d.before.timestamp_sec,
                   d.after.value, d.after.timestamp_sec, direction)
            ),
            production_concept=concept,
            semantic_direction=direction,
            supporting_frame_ids=[d.before.frame_id, d.after.frame_id],
            production_action="%s %s to %s" % (direction, d.target, d.after.value),
            confidence=min(d.before.confidence, d.after.confidence),
        )
        bundle.interpretations.append(interp)

    return bundle


class VisualReasoner:
    """Boundary for visual inference. Model is fixed; not caller-selectable."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key (falls back to ANTHROPIC_API_KEY env var,
        then to a project-root .env file — accepting either ANTHROPIC_API_KEY or
        api_key as the variable name there)."""
        if api_key is None and not os.environ.get("ANTHROPIC_API_KEY"):
            try:
                from dotenv import dotenv_values
                env_path = Path(__file__).parent.parent.parent / ".env"
                if env_path.exists():
                    values = dotenv_values(env_path)
                    found = values.get("ANTHROPIC_API_KEY") or values.get("api_key")
                    if found:
                        os.environ["ANTHROPIC_API_KEY"] = found
            except ImportError:
                pass
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def reason(self, bundle: VisualEvidenceBundle) -> VisualEvidenceBundle:
        """Populate bundle.observations and bundle.interpretations from frames.

        Returns the same bundle object with observations/interpretations added.
        Sets bundle.reasoning_error if reasoning fails.
        Sets bundle.model_metadata with honest provenance (no attestation).
        """
        if not bundle.frames:
            bundle.reasoning_error = "No frames to reason about"
            return bundle

        if not self._api_key:
            bundle.reasoning_error = (
                "ANTHROPIC_API_KEY not set. Set it to enable visual reasoning."
            )
            return bundle

        try:
            import anthropic
        except ImportError:
            bundle.reasoning_error = "anthropic SDK not installed (pip install anthropic)"
            return bundle

        content, frames_in_request = self._build_frame_content(bundle, _USER_PROMPT_TEMPLATE.format(
            n_frames=len(bundle.frames)
        ))
        if not frames_in_request:
            bundle.reasoning_error = "No frame files found on disk"
            return bundle

        response, err = self._call_model(_SYSTEM_PROMPT, content)
        if err:
            bundle.reasoning_error = err
            return bundle
        bundle.model_metadata = self._metadata_from_response(response)

        raw_text = response.content[0].text if response.content else ""
        self._parse_response(raw_text, bundle)
        return bundle

    def observe_frames(
        self, bundle: VisualEvidenceBundle, target_hint: Optional[str] = None,
    ) -> VisualEvidenceBundle:
        """Stage A: OBSERVED ONLY. No interpretation, no production concept,
        no direction — see module docstring. When target_hint names a
        specific parameter (e.g. 'Env1.Release', from a
        transcript_query_planner.VisualQueryPlan), each frame is also asked
        for that target's exact displayed value, populating
        bundle.observed_canonical_states with ObservedCanonicalState records
        that carry the frame's hash for independent traceability.

        Populates bundle.observations, bundle.observed_canonical_states, and
        bundle.unknown. Never touches bundle.interpretations — that is
        infer_from_diffs()'s job, run over the diffs this produces.
        """
        if not bundle.frames:
            bundle.reasoning_error = "No frames to reason about"
            return bundle

        if not self._api_key:
            bundle.reasoning_error = (
                "ANTHROPIC_API_KEY not set. Set it to enable visual reasoning."
            )
            return bundle

        try:
            import anthropic  # noqa: F401 — availability check, used in _call_model
        except ImportError:
            bundle.reasoning_error = "anthropic SDK not installed (pip install anthropic)"
            return bundle

        target_instruction = (
            "The specific target to read at every frame, if visible, is: %r." % target_hint
            if target_hint else
            "No specific target was named; report target_reading as all-null and focus on observations."
        )
        user_prompt = _OBSERVE_ONLY_USER_PROMPT_TEMPLATE.format(
            n_frames=len(bundle.frames), target_instruction=target_instruction,
        )
        content, frames_in_request = self._build_frame_content(bundle, user_prompt)
        if not frames_in_request:
            bundle.reasoning_error = "No frame files found on disk"
            return bundle

        response, err = self._call_model(_OBSERVE_ONLY_SYSTEM_PROMPT, content)
        if err:
            bundle.reasoning_error = err
            return bundle
        bundle.model_metadata = self._metadata_from_response(response)

        raw_text = response.content[0].text if response.content else ""
        self._parse_observe_response(raw_text, bundle, target_hint)
        return bundle

    # ------------------------------------------------------------------
    # Shared plumbing
    # ------------------------------------------------------------------

    def _build_frame_content(
        self, bundle: VisualEvidenceBundle, prompt_text: str,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt_text}]
        frames_in_request: List[str] = []
        for frame in bundle.frames:
            frame_path = Path(__file__).parent.parent.parent / frame.artifact_path
            if not frame_path.exists():
                continue
            raw = frame_path.read_bytes()
            b64 = base64.standard_b64encode(raw).decode("ascii")
            content.append({
                "type": "text",
                "text": "Frame %s at %.1f seconds:" % (frame.frame_id, frame.timestamp_sec),
            })
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })
            frames_in_request.append(frame.frame_id)
        return content, frames_in_request

    def _call_model(self, system_prompt: str, content: List[Dict[str, Any]]):
        """Returns (response, error_str). Exactly one is None."""
        import anthropic
        client = anthropic.Anthropic(api_key=self._api_key)
        try:
            response = client.messages.create(
                model=_VISUAL_MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )
            return response, None
        except Exception as exc:
            return None, "API call failed: %s" % exc

    def _metadata_from_response(self, response) -> VisualModelMetadata:
        return VisualModelMetadata(
            requested_model=_VISUAL_MODEL,
            response_model=response.model,
            request_id=response.id,
            input_tokens=response.usage.input_tokens if response.usage else None,
            output_tokens=response.usage.output_tokens if response.usage else None,
            provider="anthropic",
            provider_attestation=None,  # always null
        )

    @staticmethod
    def _extract_json(raw_text: str) -> Tuple[Optional[dict], Optional[str]]:
        json_text = raw_text.strip()
        if "```" in json_text:
            for part in json_text.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    json_text = part
                    break
        try:
            return json.loads(json_text), None
        except json.JSONDecodeError as exc:
            return None, "JSON parse failed: %s (first 200: %s)" % (exc, raw_text[:200])

    def _parse_observe_response(
        self, raw_text: str, bundle: VisualEvidenceBundle, target_hint: Optional[str],
    ) -> None:
        data, err = self._extract_json(raw_text)
        if err:
            bundle.reasoning_error = err
            return

        for frame_data in data.get("frames", []):
            frame_id = frame_data.get("frame_id", "unknown")
            ts = float(frame_data.get("timestamp_sec", 0.0))
            frame_hash = next(
                (f.artifact_hash for f in bundle.frames if f.frame_id == frame_id), ""
            )

            for obs_data in frame_data.get("observations", []):
                obs = VisualObservation(
                    frame_id=frame_id,
                    timestamp_sec=ts,
                    observation_text=obs_data.get("observation_text", ""),
                    observable_type=obs_data.get("observable_type", "general"),
                    ui_element=obs_data.get("ui_element"),
                    estimated_value=obs_data.get("estimated_value"),
                    confidence=float(obs_data.get("confidence", 0.5)),
                )
                if obs.observation_text:
                    bundle.observations.append(obs)

            reading = frame_data.get("target_reading") or {}
            if target_hint and reading.get("value"):
                bundle.observed_canonical_states.append(ObservedCanonicalState(
                    target=target_hint,
                    value=reading["value"],
                    frame_id=frame_id,
                    timestamp_sec=ts,
                    frame_hash=frame_hash,
                    confidence=float(reading.get("confidence", 0.5)),
                ))

            for unk in frame_data.get("unknown", []):
                if unk:
                    bundle.unknown.append("[t=%.1fs] %s" % (ts, unk))

    def _parse_response(self, raw_text: str, bundle: VisualEvidenceBundle) -> None:
        """Parse the model response and populate bundle observations/interpretations."""
        # Extract JSON from response (may be wrapped in markdown)
        json_text = raw_text.strip()
        if "```" in json_text:
            # Strip markdown fences
            parts = json_text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    json_text = part
                    break

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as exc:
            bundle.reasoning_error = "JSON parse failed: %s (first 200: %s)" % (
                exc, raw_text[:200]
            )
            return

        for frame_data in data.get("frames", []):
            frame_id = frame_data.get("frame_id", "unknown")
            ts = float(frame_data.get("timestamp_sec", 0.0))

            for obs_data in frame_data.get("observations", []):
                obs = VisualObservation(
                    frame_id=frame_id,
                    timestamp_sec=ts,
                    observation_text=obs_data.get("observation_text", ""),
                    observable_type=obs_data.get("observable_type", "general"),
                    ui_element=obs_data.get("ui_element"),
                    estimated_value=obs_data.get("estimated_value"),
                    confidence=float(obs_data.get("confidence", 0.5)),
                )
                if obs.observation_text:
                    bundle.observations.append(obs)

            for inf_data in frame_data.get("inferences", []):
                interp = VisualInterpretation(
                    interpretation_text=inf_data.get("interpretation_text", ""),
                    production_concept=inf_data.get("production_concept", ""),
                    semantic_direction=inf_data.get("semantic_direction", ""),
                    supporting_frame_ids=inf_data.get("supporting_frame_ids", [frame_id]),
                    production_action=inf_data.get("production_action"),
                    confidence=float(inf_data.get("confidence", 0.5)),
                )
                if interp.interpretation_text and interp.production_concept:
                    bundle.interpretations.append(interp)
