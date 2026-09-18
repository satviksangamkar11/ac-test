"""VisualReasoner — boundary for visual interpretation.

This module is the sole entry point for visual inference. It uses a FIXED
model (claude-haiku-4-5-20251001). The model is NOT selectable by callers.

Authority invariants:
    - VisualReasoner NEVER calls serum-mcp
    - VisualReasoner NEVER calls Ableton MCP
    - VisualReasoner NEVER modifies admission, capability contracts, or authority
    - VisualReasoner produces observations and interpretations ONLY
    - model_metadata.provider_attestation is ALWAYS null (no cryptographic proof)

The resulting VisualEvidenceBundle is passed to the ProducerBrain, which
converts the best interpretation into a UniversalProductionIntent and
routes it through the existing authority chain.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from serum2.source.visual_evidence import (
    VisualEvidenceBundle,
    VisualModelMetadata,
    VisualObservation,
    VisualInterpretation,
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

        client = anthropic.Anthropic(api_key=self._api_key)

        # Build content blocks: text prompt + one image per frame
        content: List[Dict[str, Any]] = []
        content.append({
            "type": "text",
            "text": _USER_PROMPT_TEMPLATE.format(n_frames=len(bundle.frames)),
        })

        frames_in_request = []
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
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            })
            frames_in_request.append(frame.frame_id)

        if not frames_in_request:
            bundle.reasoning_error = "No frame files found on disk"
            return bundle

        # Call fixed model
        try:
            response = client.messages.create(
                model=_VISUAL_MODEL,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:
            bundle.reasoning_error = "API call failed: %s" % exc
            return bundle

        # Honest model metadata — no attestation
        bundle.model_metadata = VisualModelMetadata(
            requested_model=_VISUAL_MODEL,
            response_model=response.model,
            request_id=response.id,
            input_tokens=response.usage.input_tokens if response.usage else None,
            output_tokens=response.usage.output_tokens if response.usage else None,
            provider="anthropic",
            provider_attestation=None,  # always null
        )

        # Parse structured response
        raw_text = response.content[0].text if response.content else ""
        self._parse_response(raw_text, bundle)
        return bundle

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
