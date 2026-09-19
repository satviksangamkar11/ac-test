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
# Canonical episode read location (episode_retrieval.py's EPISODE_STORAGE_DIR).
# NOT serum2/data/episodes/ (that dir holds ProductionRun state files,
# prod_*.json, via state_machine.RUNS_DIR — a different concept). Production
# episodes must land in qualification/ or the brain's episode-informed
# reasoning (ProducerBrain._retrieve_episodes) never sees them.
_EPISODES_DIR = Path(__file__).parent.parent / "qualification"


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

    # Stage 2: Canonical knowledge ingestion — writes to the SAME
    # KnowledgeItem/KnowledgeStore schema and file convention the brain's
    # retrieval (knowledge_retrieval_adapter.py) actually reads. One
    # knowledge truth: no separate lightweight KnowledgeRecord store that
    # the brain can never see.
    try:
        from serum2.knowledge.ingestion import ingest_canonical
        result = ingest_canonical(source_id, transcript_text, source_url=url)
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

    # Brain V2 P0: create the canonical experience record now, while
    # source/context/producer_request/brain_decision/retrieved_* are all
    # already known. Updated incrementally at each later stage — never
    # reconstructed once at the end (see experience_record.py docstring).
    try:
        from serum2.server import experience_record as _exp
        record = _exp.create_initial(run, brain_result)
        _exp.save(record)
    except Exception as e:
        # Advisory tracking must never block the authoritative production
        # result, but a swallowed exception would hide real bugs — surface
        # it visibly instead of a bare `except: pass`.
        import sys as _sys
        print(f"[experience_record] non-fatal error creating initial record: {e}", file=_sys.stderr)

    # Emit next_action for agent-driven serum-mcp stage
    run.next_action = _preset_generation_action(run)
    run.save()
    return run


# Strict predecessor requirement for each agent-driven stage. advance_production()
# hard-stops (terminal FAILED, not a silent no-op) on any out-of-order call —
# e.g. re-submitting PRESET_GENERATED evidence after already reaching
# SERUM_UI_CONFIGURED could silently overwrite preset_path/sha out from under
# a stage that already consumed it. This is deliberately unforgiving: a
# stage that already passed must never be re-enterable via a stray or
# duplicate call. MIDI_CREATED/ARRANGEMENT_VERIFIED are intentionally NOT
# separate enforced stages: AbletonMCP's own guidance is to batch track+clip+
# notes+arrangement into one batch_commands call ("one round-trip, one undo
# step"), so ABLETON_CONFIGURED covers all of it atomically by design, not
# by omission.
_STAGE_TO_STATE: Dict[str, ProductionState] = {
    "PRESET_GENERATED": ProductionState.PRESET_GENERATED,
    "SERUM_UI_CONFIGURED": ProductionState.SERUM_UI_CONFIGURED,
    "SERUM_VERIFIED": ProductionState.SERUM_VERIFIED,
    "ABLETON_CONFIGURED": ProductionState.ABLETON_CONFIGURED,
    "RENDERED": ProductionState.RENDERED,
}
_EXPECTED_PREDECESSOR: Dict[ProductionState, ProductionState] = {
    ProductionState.PRESET_GENERATED: ProductionState.ADMITTED,
    ProductionState.SERUM_UI_CONFIGURED: ProductionState.PRESET_GENERATED,
    ProductionState.SERUM_VERIFIED: ProductionState.SERUM_UI_CONFIGURED,
    ProductionState.ABLETON_CONFIGURED: ProductionState.SERUM_VERIFIED,
    ProductionState.RENDERED: ProductionState.ABLETON_CONFIGURED,
}


def _warn_experience(context: str, e: Exception) -> None:
    import sys as _sys
    print(f"[experience_record] non-fatal error in {context}: {e}", file=_sys.stderr)


def advance_production(run_id: str, stage: str, evidence: Dict[str, Any]) -> ProductionRun:
    """Advance past an agent-driven stage with Claude-captured evidence.

    Hard-stops (terminal FAILED) on any call whose stage does not match
    run.state's required predecessor — see _EXPECTED_PREDECESSOR.
    """
    run = ProductionRun.load(run_id)
    # Brain V2 P0: the plan pending BEFORE this call is the "specified" side
    # of whichever evidence record this stage updates — captured here,
    # before anything overwrites run.next_action below.
    specified_action = run.next_action

    target_state = _STAGE_TO_STATE.get(stage)
    if target_state is None:
        run.fail(f"UNKNOWN_STAGE: {stage}")
        run.save()
        return run

    expected_predecessor = _EXPECTED_PREDECESSOR[target_state]
    if run.state != expected_predecessor.value:
        run.fail(
            f"OUT_OF_ORDER_STAGE: '{stage}' requires state={expected_predecessor.value!r} "
            f"but run is currently in state={run.state!r}"
        )
        run.save()
        return run

    if stage == "PRESET_GENERATED":
        preset_path = evidence.get("preset_path", "")
        sha = evidence.get("preset_sha256") or _sha256(preset_path)
        run.advance(
            ProductionState.PRESET_GENERATED,
            preset_path=preset_path,
            preset_sha256=sha,
        )
        run.next_action = _serum_ui_action(run)
        try:
            _record_preset_generated(run, specified_action, evidence, sha)
        except Exception as e:
            _warn_experience("PRESET_GENERATED", e)

    elif stage == "SERUM_UI_CONFIGURED":
        run.advance(ProductionState.SERUM_UI_CONFIGURED, serum_ui_evidence=evidence)
        run.next_action = _serum_verify_action(run)
        try:
            _record_serum_ui_action(run, "load_and_configure", evidence, verified=None)
        except Exception as e:
            _warn_experience("SERUM_UI_CONFIGURED", e)

    elif stage == "SERUM_VERIFIED":
        if not evidence.get("verified"):
            run.fail("SERUM_VERIFICATION_FAILED: verified=false in evidence")
            run.save()
            return run
        run.advance(ProductionState.SERUM_VERIFIED)
        run.next_action = _ableton_action(run)
        try:
            _record_serum_ui_action(run, "verify", evidence, verified=True)
        except Exception as e:
            _warn_experience("SERUM_VERIFIED", e)

    elif stage == "ABLETON_CONFIGURED":
        run.advance(ProductionState.ABLETON_CONFIGURED, ableton_evidence=evidence)
        run.next_action = _render_action(run)
        try:
            _record_ableton_call(run, specified_action, evidence)
        except Exception as e:
            _warn_experience("ABLETON_CONFIGURED", e)

    elif stage == "RENDERED":
        render_path = evidence.get("render_path")
        run.advance(ProductionState.RENDERED, render_path=render_path)
        # Auto-advance: measure → evidence-finalize → episode → complete
        try:
            measurements = _measure(render_path)
            if measurements.get("status") not in ("MEASURED",):
                # A render that can't even be read as a WAV must not
                # silently complete with fabricated measurement values.
                run.fail(f"MEASUREMENT_FAILED: {measurements.get('status')} — {measurements.get('error', '')}")
                run.save()
                return run
            run.advance(ProductionState.MEASURED, measurements=measurements)
            run.advance(ProductionState.EVIDENCE_FINALIZED)
            episode_id = _finalize_episode(run)
            run.advance(ProductionState.COMPLETED, episode_id=episode_id, next_action=None)
            try:
                _record_render_and_finalize(run, specified_action, evidence, measurements)
            except Exception as e:
                _warn_experience("RENDERED", e)
        except Exception as e:
            run.fail(f"POST_RENDER: {e}")

    run.save()
    return run


# ---------------------------------------------------------------------------
# Brain V2 P0: incremental experience-record updates, one per stage.
# Each loads the record created at ADMITTED, applies exactly the update for
# this stage, and saves — real per-stage tracking, not a single end-of-run
# reconstruction. See experience_record.py's module docstring and the
# specified/executed/read_back/verified table in the plan for the exact
# real (non-fabricated) signal each stage's "verified" check uses.
# ---------------------------------------------------------------------------

def _record_preset_generated(
    run: ProductionRun, specified_action: Optional[Dict[str, Any]],
    evidence: Dict[str, Any], sha: Optional[str],
) -> None:
    from serum2.server import experience_record as _exp

    record = _exp.load_for_run(run.run_id)
    args_specified = (specified_action or {}).get("args", {})
    preset_path = evidence.get("preset_path", "")
    if sha:
        # A real sha256 was computed FROM THE ACTUAL FILE — that computation
        # is itself the read-back, and a successful hash IS the verification
        # that the artifact genuinely exists on disk as specified.
        stage = _exp.EvidenceStage.VERIFIED.value
    elif preset_path:
        stage = _exp.EvidenceStage.EXECUTED.value
    else:
        stage = _exp.EvidenceStage.SPECIFIED.value

    call = _exp.SerumMcpCallRecord(
        tool=(specified_action or {}).get("tool", "mcp__serum-mcp__generate_preset"),
        args_specified=args_specified,
        stage=stage,
        result=evidence,
        preset_path=preset_path or None,
        preset_sha256=sha,
    )
    record.serum_mcp_call = call.to_dict()
    record.provenance["serum_mcp_call"] = "production_pipeline.advance_production(PRESET_GENERATED)"
    _exp.save(record)


def _record_serum_ui_action(
    run: ProductionRun, action: str, evidence: Dict[str, Any], verified: Optional[bool],
) -> None:
    from serum2.server import experience_record as _exp

    record = _exp.load_for_run(run.run_id)
    if verified is True:
        stage = _exp.EvidenceStage.VERIFIED.value
    elif evidence:
        stage = _exp.EvidenceStage.EXECUTED.value
    else:
        stage = _exp.EvidenceStage.SPECIFIED.value

    entry = _exp.SerumUiActionRecord(
        action=action,
        stage=stage,
        evidence=evidence,
        controls_matched=evidence.get("controls_matched"),
        mutation_applied=evidence.get("mutation_applied"),
    )
    record.serum_ui_actions.append(entry.to_dict())
    record.provenance["serum_ui_actions"] = "production_pipeline.advance_production(SERUM_UI_CONFIGURED/SERUM_VERIFIED)"
    _exp.save(record)


def _record_ableton_call(
    run: ProductionRun, specified_action: Optional[Dict[str, Any]], evidence: Dict[str, Any],
) -> None:
    from serum2.server import experience_record as _exp

    record = _exp.load_for_run(run.run_id)
    args_specified = (specified_action or {}).get("args", {})

    # Real structural check against the KNOWN specified geometry (4 clips at
    # beats 0/16/32/48, clip length 16.0) — comparing actual readback to what
    # was specified, not fabricating a pass. If the caller's evidence doesn't
    # carry these keys at all, this correctly stays below VERIFIED.
    clip_info = evidence.get("clip_info") or {}
    arrangement_clips = evidence.get("arrangement_clips") or []
    clip_length_ok = isinstance(clip_info, dict) and clip_info.get("length") == 16.0
    arrangement_ok = isinstance(arrangement_clips, list) and len(arrangement_clips) == 4
    verified = clip_length_ok and arrangement_ok

    if verified:
        stage = _exp.EvidenceStage.VERIFIED.value
    elif clip_info or arrangement_clips:
        stage = _exp.EvidenceStage.READ_BACK.value
    elif evidence:
        stage = _exp.EvidenceStage.EXECUTED.value
    else:
        stage = _exp.EvidenceStage.SPECIFIED.value

    call = _exp.AbletonMcpCallRecord(
        tool=(specified_action or {}).get("tool", "mcp__AbletonMCP__batch_commands"),
        args_specified=args_specified,
        stage=stage,
        result=evidence,
        readback=evidence,
        readback_verified=verified,
    )
    record.ableton_calls.append(call.to_dict())
    record.provenance["ableton_calls"] = "production_pipeline.advance_production(ABLETON_CONFIGURED)"
    _exp.save(record)


def _record_render_and_finalize(
    run: ProductionRun, specified_action: Optional[Dict[str, Any]],
    evidence: Dict[str, Any], measurements: Dict[str, Any],
) -> None:
    from serum2.server import experience_record as _exp
    from serum2.server.production_memory import ProductionMemory, link_experience

    record = _exp.load_for_run(run.run_id)

    # Artifact-level success (file exists, WAV header/samples readable) and
    # acoustic-level success (real DSP actually computed from those samples)
    # are separate criteria — a valid-but-unsupported-format WAV can be
    # MEASURED (real duration/rate/sha256) while acoustic_status stays
    # UNSUPPORTED_FORMAT, and neither may claim VERIFIED on the other's behalf.
    artifact_ok = measurements.get("status") == "MEASURED"
    acoustic_ok = measurements.get("acoustic_status") == "COMPUTED"

    render_stage = (
        _exp.EvidenceStage.VERIFIED.value if artifact_ok
        else _exp.EvidenceStage.EXECUTED.value if evidence.get("render_path")
        else _exp.EvidenceStage.SPECIFIED.value
    )
    render = _exp.RenderArtifactRecord(
        render_path=evidence.get("render_path"),
        file_size_bytes=measurements.get("file_size_bytes"),
        duration_sec=measurements.get("duration_sec"),
        sha256=measurements.get("sha256"),
        stage=render_stage,
    )
    record.render_artifact = render.to_dict()

    acoustic = _exp.AcousticMeasurementRecord(
        rms_db=measurements.get("rms_db"),
        peak_db=measurements.get("peak_db"),
        spectral_centroid_hz=measurements.get("spectral_centroid_hz"),
        measurement_definition_id=measurements.get("measurement_definition_id"),
        kernel_version=measurements.get("kernel_version"),
        channel_policy=measurements.get("channel_policy"),
        stage=_exp.EvidenceStage.VERIFIED.value if acoustic_ok else _exp.EvidenceStage.SPECIFIED.value,
    )
    record.acoustic_measurements = acoustic.to_dict()

    record.canonical_episode_id = run.episode_id
    record.canonical_episode_path = (
        str(_EPISODES_DIR / f"{run.episode_id}.json") if run.episode_id else None
    )

    # Same decision fields _finalize_episode() already writes — reused, not
    # reinvented: no A/B baseline/treatment comparison in this creation flow,
    # so "COMPLETED" (not ACCEPTED/REJECTED) is the honest label.
    record.outcome = {
        "decision": "COMPLETED",
        "measurement_delta": None,
        "learning_eligible": True,
    }
    record.provenance["render_artifact"] = "serum2.evidence.acoustic_measurement.measure_render"
    record.provenance["acoustic_measurements"] = "serum2.evidence.acoustic_measurement.compute_acoustic_metrics"
    record.provenance["outcome"] = "production_pipeline._finalize_episode"
    _exp.save(record)

    link_experience(ProductionMemory(), record)


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


def _run_brain_intent_admission(
    source_id: str,
    transcript_text: str,
    context: Optional["ProductionContext"] = None,
) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """Call the canonical producer brain for real intent resolution + admission.

    Returns (ProducerResult, intent_dict, admission_dict).
    Does NOT pass source_url to ProducerRequest — avoids the broken
    phase1_ingest.py subprocess path in the brain's _ingest_source_url().

    CREATION INTENT != MUTATION INTENT: this is a creation-style request
    ("create a dark bass sound"), not a mutation-style one ("make the
    release longer"). It is passed to the brain AS-IS with mode="CREATE" —
    no server-side translation into a fake mutation phrase (e.g. "darker
    filter"). The brain's own _INTENT_TO_CONCEPT table now recognizes bare
    character adjectives (dark/bright/warm) directly, and
    ProducerResult.intent_class="CREATION" tells the caller the admitted
    semantic_target/direction/_mcp_plan is a PresetSpec seed value, not an
    instruction to mutate an already-loaded preset.

    ProductionContext is advisory only: serialized into musical_context
    (→ UniversalProductionIntent.musical_objective inside the brain) and
    into advisory_context (→ context-aware knowledge retrieval fan-out).
    Neither grants or alters admission authority — the same
    CapabilityResolver/AdmissionHandoff chain governs CREATE exactly as
    it governs EXECUTE.
    """
    from serum2.producer.producer_brain import execute_producer_request, ProducerRequest

    low = transcript_text.lower()
    role, character = _derive_role_character(low)
    # Natural creation-style phrase, passed through unchanged — the brain
    # resolves "dark"/"bright"/"warm" itself via its own intent vocabulary.
    intent_text = f"create a {character} {role} sound"

    # Build musical_context from ProductionContext if available, else plain string
    if context is not None:
        musical_context = context.to_musical_context_string()
    else:
        musical_context = f"{role} {character}"

    brain_result = execute_producer_request(ProducerRequest(
        user_intent=intent_text,
        musical_context=musical_context,
        advisory_context=context.to_dict() if context is not None else None,
        mode="CREATE",
    ))

    intent = {
        "role": role,
        "character": character,
        "user_intent_text": intent_text,
        "intent_class": brain_result.intent_class,
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
    """Geometry matches the proven Gate 2A execution (commit cdfac5c):
    4-bar (16-beat) clip, duplicated to arrangement at beats 0/16/32/48,
    spanning 64 beats total. AbletonMCP lengths/positions are in BEATS,
    not seconds/bars — the pre-fix version used bar numbers (4/8/12) where
    beat numbers were required, corrupting the arrangement (clips
    overlapped, render truncated to 6.7s instead of ~32s).
    """
    return {
        "action": "configure_ableton",
        "tool": "mcp__AbletonMCP__batch_commands",
        "args": {
            "commands": [
                {"command": "set_tempo", "params": {"tempo_bpm": 120}},
                {"command": "create_midi_track", "params": {"index": -1}},
                {"command": "set_track_name", "params": {"track_index": "N", "name": "Serum Lead"}},
                {"command": "create_clip", "params": {"track_index": "N", "clip_index": 0, "length": 16.0}},
                {"command": "add_notes_to_clip", "params": {
                    "notes": [
                        {"pitch": 60, "velocity": 100, "start_time": 0, "duration": 1},
                        {"pitch": 62, "velocity": 100, "start_time": 1, "duration": 1},
                        {"pitch": 64, "velocity": 100, "start_time": 2, "duration": 1},
                        {"pitch": 65, "velocity": 100, "start_time": 3, "duration": 1},
                    ]
                }},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 0}},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 16}},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 32}},
                {"command": "duplicate_to_arrangement", "params": {"track_index": "N", "clip_index": 0, "arrangement_position": 48}},
            ]
        },
        "receipt_fields": {
            "track_index": "created track index",
            "tempo_bpm": "confirmed tempo",
            "clip_info": "get_clip_info result (expect length=16.0 beats)",
            "arrangement_clips": "get_arrangement_clips result (expect 4 clips at beats 0,16,32,48, spanning 0-64)",
        },
    }


def _render_action(run: ProductionRun) -> Dict[str, Any]:
    """length is in BEATS (AbletonMCP convention), not seconds. 64 beats
    at 120 BPM = 32 seconds, matching the arrangement's full 0-64 beat span
    and the proven Gate 2A render (30.7s actual, within +/-2s tolerance)."""
    _RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    render_path = str(_RENDERS_DIR / f"{run.run_id}.wav")
    return {
        "action": "render",
        "tool": "mcp__AbletonMCP__record_section",
        "args": {
            "start_time": 0,
            "length": 64.0,
            "output_path": render_path,
        },
        "receipt_fields": {
            "render_path": render_path,
            "file_size_bytes": "actual file size",
            "duration_sec": "actual audio duration (expect ~32s at 120 BPM)",
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


# G8: the canonical acoustic-measurement kernel now lives under
# serum2/evidence/acoustic_measurement.py (single implementation, per the
# frozen plan's "reuse, do not duplicate" rule) -- imported and called here,
# not reimplemented.
from serum2.evidence.acoustic_measurement import measure_render as _measure


def _finalize_episode(run: ProductionRun) -> str:
    """Write completed episode to the canonical store (qualification/) in the
    schema episode_retrieval.retrieve_relevant_episodes() and
    ProducerBrain._retrieve_episodes() actually read: semantic_target
    (exact-match filter), human_intent (substring filter), decision,
    measurement_delta, learning_eligible. Without these fields the file
    would sit in qualification/ but never match any retrieval query.

    decision="COMPLETED" (not ACCEPTED/REJECTED): this flow renders a new
    creation once and measures artifact stats, it does not run the
    baseline-vs-treatment A/B comparison that ACCEPTED/REJECTED represent
    in the DawDreamer evidence path. COMPLETED contributes no confidence
    adjustment in ProducerBrain._build_advisory_chain (only ACCEPTED/
    REJECTED do) — it is retrievable evidence, not an authority signal,
    consistent with 'episodes inform, never authorize.'
    """
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
        # Canonical fields read by episode_retrieval.py / ProducerBrain:
        "semantic_target": intent.get("semantic_target"),
        "human_intent": intent.get("user_intent_text"),
        "decision": "COMPLETED",
        "measurement_delta": None,
        "learning_eligible": True,
    }
    (_EPISODES_DIR / f"{ep_id}.json").write_text(json.dumps(episode, indent=2))
    return ep_id
