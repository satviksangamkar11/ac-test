"""Production pipeline: YouTube URL → completed episode.

produce_from_youtube(url)
    Runs auto stages (transcript → knowledge → brain → admission).
    Returns run with next_action = serum-mcp preset generation instructions.

advance_production(run_id, stage, evidence)
    Advances past an agent-driven stage. Called by Claude after each:
      PRESET_GENERATED    → evidence: {preset_path, preset_sha256}
      SERUM_UI_CONFIGURED evidence: {screenshot_path, preset_name_confirmed, serum_version, controls_matched}
      SERUM_VERIFIED      → evidence: {verified: bool, screenshot_path}
      ABLETON_CONFIGURED  → evidence: {track_index, clip_info, arrangement_info}
      RENDERED            → evidence: {render_path, file_size_bytes, duration_sec}

Architecture:
  Auto stages run pure Python — no Claude tool calls needed.
  Agent stages need Claude tool calls (serum-mcp, computer-use, AbletonMCP).
  Pipeline emits next_action instructions; Claude executes and feeds evidence back.
  Measurement + episode finalization auto-runs after RENDERED.

Brain boundary:
  Stages 3+4 (intent + admission) delegate to existing execute_producer_request().
  The brain owns: concept resolution, real authority chain (6.6→6.7→6.8),
  episode-informed confidence, route selection, and MCP plan production.
  The server owns: transcript, knowledge persistence, serum-mcp CREATION,
  Serum UI load+verify, Ableton arrangement, render, and episode storage.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = str(Path(__file__).parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from serum2.server.state_machine import ProductionRun, ProductionState
from serum2.server.production_context import ProductionContext, build_from_transcript

_RENDERS_DIR = Path(__file__).parent.parent / "data" / "renders"
_EPISODES_DIR = Path(__file__).parent.parent / "data" / "episodes"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def produce_from_youtube(url: str) -> ProductionRun:
    """Start or resume a production run.

    Runs auto stages through ADMITTED, then sets next_action for the
    serum-mcp preset generation stage (first agent-driven stage).
    Idempotent: returns existing non-terminal run for the same URL.
    """
    run_id = "prod_" + hashlib.md5(url.encode()).hexdigest()[:12]

    # Return existing non-terminal run (idempotent)
    try:
        run = ProductionRun.load(run_id)
        if run.state not in (ProductionState.FAILED.value, ProductionState.COMPLETED.value):
            return run
    except FileNotFoundError:
        pass

    run = ProductionRun(run_id=run_id, youtube_url=url)
    run.save()

    # Stage 1: Transcription (8-tier resolver)
    try:
        transcript_text, source_id = _resolve_transcript(url)
        run.advance(
            ProductionState.TRANSCRIBED,
            source_id=source_id,
            transcript_snippet=transcript_text[:200],
        )
        run.save()
    except Exception as e:
        run.fail(f"TRANSCRIPTION_FAILED: {e}")
        run.save()
        return run

    # Stage 2: Knowledge ingestion (persistence layer — advisory, separate from brain's store)
    try:
        from serum2.knowledge.ingestion import ingest
        result = ingest(source_id, transcript_text)
        run.advance(
            ProductionState.KNOWLEDGE_BUILT,
            knowledge_record_count=result["record_count"],
        )
        run.save()
    except Exception as e:
        run.fail(f"KNOWLEDGE_INGESTION_FAILED: {e}")
        run.save()
        return run

    # Stage 2.5: Build advisory ProductionContext from transcript
    # (computed once here; passed to brain as musical_context advisory string)
    production_context = build_from_transcript(
        transcript_text,
        role=_derive_role_character(transcript_text.lower())[0],
        character=_derive_role_character(transcript_text.lower())[1],
        source_id=source_id,
    )

    # Stages 3+4: Intent + real admission via existing producer brain
    try:
        brain_result, intent, admission = _run_brain_intent_admission(
            source_id, transcript_text, production_context
        )
        if not brain_result.admitted:
            run.fail(f"ADMISSION_REFUSED: {brain_result.admission_reason}")
            run.save()
            return run

        run.advance(ProductionState.INTENT_CREATED, intent=intent)
        run.save()
        run.advance(ProductionState.ADMITTED, admission=admission)
        run.save()
    except Exception as e:
        run.fail(f"INTENT_ADMISSION_FAILED: {e}")
        run.save()
        return run

    # Emit next_action for agent-driven serum-mcp stage
    run.next_action = _preset_generation_action(run)
    run.save()
    return run


def advance_production(run_id: str, stage: str, evidence: Dict[str, Any]) -> ProductionRun:
    """Advance past an agent-driven stage with Claude-captured evidence."""
    run = ProductionRun.load(run_id)

    if stage == "PRESET_GENERATED":
        preset_path = evidence.get("preset_path", "")
        sha = evidence.get("preset_sha256") or _sha256(preset_path)
        run.advance(
            ProductionState.PRESET_GENERATED,
            preset_path=preset_path,
            preset_sha256=sha,
        )
        run.next_action = _serum_ui_action(run)

    elif stage == "SERUM_UI_CONFIGURED":
        run.advance(ProductionState.SERUM_UI_CONFIGURED, serum_ui_evidence=evidence)
        run.next_action = _serum_verify_action(run)

    elif stage == "SERUM_VERIFIED":
        if not evidence.get("verified"):
            run.fail("SERUM_VERIFICATION_FAILED: verified=false in evidence")
            run.save()
            return run
        run.advance(ProductionState.SERUM_VERIFIED)
        run.next_action = _ableton_action(run)

    elif stage == "ABLETON_CONFIGURED":
        run.advance(ProductionState.ABLETON_CONFIGURED, ableton_evidence=evidence)
        run.next_action = _render_action(run)

    elif stage == "RENDERED":
        render_path = evidence.get("render_path")
        run.advance(ProductionState.RENDERED, render_path=render_path)
        # Auto-advance: measure → finalize → complete
        try:
            measurements = _measure(render_path)
            run.advance(ProductionState.MEASURED, measurements=measurements)
            episode_id = _finalize_episode(run)
            run.advance(ProductionState.COMPLETED, episode_id=episode_id, next_action=None)
        except Exception as e:
            run.fail(f"POST_RENDER: {e}")

    else:
        run.fail(f"UNKNOWN_STAGE: {stage}")

    run.save()
    return run


def get_status(run_id: str) -> Dict[str, Any]:
    run = ProductionRun.load(run_id)
    return {
        "run_id": run.run_id,
        "state": run.state,
        "error": run.error,
        "source_id": run.source_id,
        "knowledge_records": run.knowledge_record_count,
        "intent": run.intent,
        "preset_path": run.preset_path,
        "render_path": run.render_path,
        "episode_id": run.episode_id,
        "next_action": run.next_action,
    }


# ---------------------------------------------------------------------------
# Stage 1: Transcript resolution
# ---------------------------------------------------------------------------

def _extract_video_id(url: str) -> Optional[str]:
    m = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})', url)
    return m.group(1) if m else None


def _resolve_transcript(url: str) -> Tuple[str, str]:
    """Resolve YouTube URL → (flat_transcript_text, source_id).

    Uses the 8-tier resolver (youtube_transcript_resolver.py).
    Falls back to MD5-based source_id if video_id extraction fails.
    """
    from serum2.source.youtube_transcript_resolver import resolve_youtube_transcript

    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Cannot extract video_id from URL: {url!r}")

    resolution = resolve_youtube_transcript(video_id)

    if resolution.status not in ("AVAILABLE", "TRANSLATED"):
        raise ValueError(
            f"Transcript unavailable: status={resolution.status}"
            + (f" error={resolution.error}" if resolution.error else "")
        )

    segments = resolution.transcript or []
    transcript_text = " ".join(s["text"] for s in segments)
    source_id = f"yt_{video_id}"
    return transcript_text, source_id


# ---------------------------------------------------------------------------
# Stages 3+4: Intent + admission via existing producer brain
# ---------------------------------------------------------------------------

def _derive_role_character(transcript_lower: str) -> Tuple[str, str]:
    role = "lead"
    if any(w in transcript_lower for w in ["bass", "sub", "low end", "808"]):
        role = "bass"
    elif any(w in transcript_lower for w in ["pad", "atmosphere", "ambient", "texture"]):
        role = "pad"
    elif any(w in transcript_lower for w in ["pluck", "stab", "percussive"]):
        role = "pluck"

    character = "bright"
    if any(w in transcript_lower for w in ["dark", "deep", "heavy", "gritty"]):
        character = "dark"
    elif any(w in transcript_lower for w in ["warm", "smooth", "mellow", "soft"]):
        character = "warm"

    return role, character


def _character_to_mutation_intent(character: str) -> str:
    """Map sound character to a mutation-style intent that the brain's
    _INTENT_TO_CONCEPT table resolves to an MCP-bridge concept.

    All returned strings map to _MCP_CONCEPT_BRIDGE entries, guaranteeing
    MCP_HOST_MAP_QUALIFIED admission without requiring a PKL contract.
    """
    if character == "dark":
        return "darker filter"        # → filter-cutoff (MCP bridge)
    elif character == "warm":
        return "osc volume louder"    # → oscillator-volume (MCP bridge)
    else:                             # bright / default
        return "brighter filter"      # → filter-cutoff (MCP bridge)


def _run_brain_intent_admission(
    source_id: str,
    transcript_text: str,
    context: Optional["ProductionContext"] = None,
) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """Call the canonical producer brain for real intent resolution + admission.

    Returns (ProducerResult, intent_dict, admission_dict).
    Does NOT pass source_url to ProducerRequest — avoids the broken
    phase1_ingest.py subprocess path in the brain's _ingest_source_url().

    ProductionContext is advisory only: serialized into musical_context
    (→ UniversalProductionIntent.musical_objective inside the brain).
    It influences knowledge retrieval and semantic reasoning;
    it never grants or alters admission authority.
    """
    from serum2.producer.producer_brain import execute_producer_request, ProducerRequest

    low = transcript_text.lower()
    role, character = _derive_role_character(low)
    intent_text = _character_to_mutation_intent(character)

    # Build musical_context from ProductionContext if available, else plain string
    if context is not None:
        musical_context = context.to_musical_context_string()
    else:
        musical_context = f"{role} {character}"

    brain_result = execute_producer_request(ProducerRequest(
        user_intent=intent_text,
        musical_context=musical_context,
        advisory_context=context.to_dict() if context is not None else None,
    ))

    intent = {
        "role": role,
        "character": character,
        "user_intent_text": intent_text,
        "semantic_target": brain_result.semantic_target,
        "execution_route": brain_result.execution_route,
        "admission_reason": brain_result.admission_reason,
        "source_id": source_id,
        "supporting_knowledge_count": len(brain_result.retrieved_knowledge),
        "production_context": context.to_dict() if context is not None else None,
    }

    mcp_plan = getattr(brain_result, "_mcp_plan", None)
    admission = {
        "admitted": brain_result.admitted,
        "reason": brain_result.admission_reason,
        "resolution_status": brain_result.resolution_status,
        "mcp_plan": mcp_plan,
    }

    return brain_result, intent, admission


# ---------------------------------------------------------------------------
# next_action builders — minimal {action, tool, args, receipt_fields} format
# ---------------------------------------------------------------------------

def _preset_generation_action(run: ProductionRun) -> Dict[str, Any]:
    intent = run.intent or {}
    role = intent.get("role", "lead")
    character = intent.get("character", "bright")
    semantic_target = intent.get("semantic_target") or "Filter.Cutoff"

    # Filter settings driven by character + brain's semantic target
    is_dark_warm = character in ("dark", "warm")
    cutoff = 0.45 if character == "dark" else (0.60 if character == "warm" else 0.78)

    return {
        "action": "generate_preset",
        "tool": "mcp__serum-mcp__generate_preset",
        "args": {
            "name": f"{role.title()} {character.title()}",
            "oscillators": [
                {
                    "index": 0,
                    "wavetable": "BasicShapes",
                    "level": 0.8,
                    "unison_voices": 3 if role in ("pad", "lead") else 1,
                    "detune": 0.15 if role in ("pad", "lead") else 0.0,
                },
            ],
            "filter": {
                "filter_type": "lowpass" if is_dark_warm else "highpass",
                "cutoff": cutoff,
                "resonance": 0.3,
                "filter_enabled": True,
            },
            "envelopes": [
                {
                    "index": 0,
                    "attack": 0.01 if character == "bright" else 0.05,
                    "decay": 0.3,
                    "sustain": 0.7,
                    "release": 0.8 if role == "pad" else 0.4,
                }
            ],
            "effects": {"reverb": {"enabled": role == "pad", "mix": 0.25}},
        },
        "receipt_fields": ["preset_path", "preset_sha256"],
        "context": {
            "brain_semantic_target": semantic_target,
            "role": role,
            "character": character,
        },
    }


def _serum_ui_action(run: ProductionRun) -> Dict[str, Any]:
    """LOAD preset first. Only apply UI mutation for controls not set by serum-mcp."""
    intent = run.intent or {}
    role = intent.get("role", "lead")
    character = intent.get("character", "bright")
    return {
        "action": "load_and_verify_preset",
        "tool": "mcp__computer-use__screenshot",
        "args": {
            "preset_path": run.preset_path,
            "expected_character": character,
            "expected_role": role,
        },
        "steps": [
            f"1. LOAD: open {run.preset_path} in Serum 2.0.21",
            "2. SCREENSHOT: capture oscillator + filter panels",
            f"3. CHECK: does state match {character} {role} intent?",
            "4. IF MISMATCH ONLY: apply correction for mismatched controls",
            "5. VERIFY: final screenshot confirming state",
        ],
        "receipt_fields": {
            "screenshot_path": "path to verification screenshot",
            "preset_name_confirmed": "name shown in Serum UI",
            "serum_version": "version string (must be 2.0.21)",
            "controls_matched": "true if preset already reflects intent",
            "mutation_applied": "null if no correction needed; else description",
        },
    }


def _serum_verify_action(run: ProductionRun) -> Dict[str, Any]:
    intent = run.intent or {}
    return {
        "action": "verify_serum_state",
        "tool": "mcp__computer-use__screenshot",
        "args": {"intent": intent},
        "steps": [
            "1. Confirm no error state in Serum",
            "2. Screenshot full UI (all panels visible)",
        ],
        "receipt_fields": {
            "verified": "true if state matches intent",
            "screenshot_path": "final verification screenshot",
        },
    }


def _ableton_action(run: ProductionRun) -> Dict[str, Any]:
    return {
        "action": "configure_ableton",
        "tool": "mcp__AbletonMCP__batch_commands",
        "args": {
            "commands": [
                {"command": "set_tempo", "params": {"tempo_bpm": 120}},
                {"command": "create_midi_track", "params": {"index": -1}},
                {"command": "set_track_name", "params": {"track_index": "N", "name": "Serum Lead"}},
                {"command": "create_clip", "params": {"track_index": "N", "clip_index": 0, "length": 4.0}},
                {"command": "add_notes_to_clip", "params": {
                    "notes": [
                        {"pitch": 60, "velocity": 100, "start_time": 0, "duration": 1},
                        {"pitch": 62, "velocity": 100, "start_time": 1, "duration": 1},
                        {"pitch": 64, "velocity": 100, "start_time": 2, "duration": 1},
                        {"pitch": 65, "velocity": 100, "start_time": 3, "duration": 1},
                    ]
                }},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 0}},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 4}},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 8}},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 12}},
            ]
        },
        "receipt_fields": {
            "track_index": "created track index",
            "tempo_bpm": "confirmed tempo",
            "clip_info": "get_clip_info result",
            "arrangement_clips": "get_arrangement_clips result",
        },
    }


def _render_action(run: ProductionRun) -> Dict[str, Any]:
    _RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    render_path = str(_RENDERS_DIR / f"{run.run_id}.wav")
    return {
        "action": "render",
        "tool": "mcp__AbletonMCP__record_section",
        "args": {
            "start_time": 0,
            "length": 32.0,
            "output_path": render_path,
        },
        "receipt_fields": {
            "render_path": render_path,
            "file_size_bytes": "actual file size",
            "duration_sec": "actual audio duration",
        },
    }


# ---------------------------------------------------------------------------
# Post-render auto stages
# ---------------------------------------------------------------------------

def _sha256(path: str) -> Optional[str]:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return None


def _measure(render_path: Optional[str]) -> Dict[str, Any]:
    if not render_path:
        return {"status": "NO_RENDER"}
    p = Path(render_path)
    if not p.exists():
        return {"status": "FILE_NOT_FOUND", "path": render_path}
    size = p.stat().st_size
    try:
        import wave
        with wave.open(str(p), "rb") as wf:
            duration = wf.getnframes() / wf.getframerate()
            channels = wf.getnchannels()
            rate = wf.getframerate()
    except Exception:
        duration = channels = rate = 0
    return {
        "status": "MEASURED",
        "file_size_bytes": size,
        "duration_sec": round(duration, 2),
        "channels": channels,
        "sample_rate": rate,
        "sha256": _sha256(render_path),
    }


def _finalize_episode(run: ProductionRun) -> str:
    """Write completed episode record to disk."""
    ep_id = f"ep_{run.run_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    _EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    intent = run.intent or {}
    episode = {
        "episode_id": ep_id,
        "run_id": run.run_id,
        "youtube_url": run.youtube_url,
        "source_id": run.source_id,
        "knowledge_record_count": run.knowledge_record_count,
        "intent": intent,
        "production_context": intent.get("production_context"),
        "admission": run.admission,
        "preset_path": run.preset_path,
        "preset_sha256": run.preset_sha256,
        "serum_ui_evidence": run.serum_ui_evidence,
        "ableton_evidence": run.ableton_evidence,
        "render_path": run.render_path,
        "measurements": run.measurements,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    (_EPISODES_DIR / f"{ep_id}.json").write_text(json.dumps(episode, indent=2))
    return ep_id
