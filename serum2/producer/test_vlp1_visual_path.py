"""VLP-1 replay test: visual episode → retrieval → intent reconstruction.

Verifies:
1. Visual evidence bundle can be persisted and reloaded
2. Reloaded bundle contains observations with timestamp/hash provenance
3. Best interpretation from reloaded bundle → valid UniversalProductionIntent
4. Reconstructed intent has concept + direction that ProducerBrain can process
5. ProducerBrain produces non-error result from reconstructed intent

Does NOT re-run vision or re-download video.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_visual_evidence_schema():
    """VisualEvidenceBundle round-trips through to_dict / load."""
    from serum2.source.visual_evidence import (
        VisualEvidenceBundle, VisualFrameArtifact, VisualObservation,
        VisualInterpretation, VisualModelMetadata, TranscriptSufficiency,
    )

    bundle = VisualEvidenceBundle(
        source_url="https://www.youtube.com/watch?v=k6OBzXdcFtA",
        source_id="yt_k6OBzXdcFtA",
        video_id="k6OBzXdcFtA",
    )
    bundle.frames.append(VisualFrameArtifact(
        frame_id="frame_yt_k6OBzXdcFtA_00030000",
        source_url=bundle.source_url,
        source_id=bundle.source_id,
        video_id=bundle.video_id,
        timestamp_sec=30.0,
        artifact_path="serum2/data/visual_frames/yt_k6OBzXdcFtA/frame_yt_k6OBzXdcFtA_00030000.jpg",
        artifact_hash="a" * 64,
    ))
    bundle.observations.append(VisualObservation(
        frame_id="frame_yt_k6OBzXdcFtA_00030000",
        timestamp_sec=30.0,
        observation_text="The Serum 2 filter cutoff knob is visible at approximately 25% of its range.",
        observable_type="ui_control",
        ui_element="filter_cutoff_knob",
        estimated_value="25%",
        confidence=0.85,
    ))
    bundle.interpretations.append(VisualInterpretation(
        interpretation_text="The producer reduced filter cutoff to darken the bass sound.",
        production_concept="filter-cutoff",
        semantic_direction="decrease",
        supporting_frame_ids=["frame_yt_k6OBzXdcFtA_00030000"],
        production_action="Reduce the filter cutoff to approximately 25% to darken the sound.",
        confidence=0.80,
    ))
    bundle.model_metadata = VisualModelMetadata(
        requested_model="claude-haiku-4-5-20251001",
        response_model="claude-haiku-4-5-20251001",
        request_id="msg_test_001",
        provider_attestation=None,  # always null
    )
    bundle.transcript_sufficiency = TranscriptSufficiency(
        status="INSUFFICIENT_OPERATIONAL",
        reason="Only 1 knowledge item in canonical store",
        evidence_item_count=1,
    )

    # Round-trip through dict
    d = bundle.to_dict()
    assert d["source_url"] == bundle.source_url
    assert len(d["frames"]) == 1
    assert len(d["observations"]) == 1
    assert len(d["interpretations"]) == 1
    assert d["model_metadata"]["provider_attestation"] is None
    assert d["transcript_sufficiency"]["status"] == "INSUFFICIENT_OPERATIONAL"

    # Round-trip through file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        f.write(json.dumps(d))
        tmp_path = f.name

    try:
        loaded = VisualEvidenceBundle.load(tmp_path)
        assert loaded.source_url == bundle.source_url
        assert len(loaded.frames) == 1
        assert loaded.frames[0].timestamp_sec == 30.0
        assert loaded.frames[0].artifact_hash == "a" * 64
        assert len(loaded.observations) == 1
        assert "filter cutoff" in loaded.observations[0].observation_text.lower()
        # Observed and inferred are separate
        assert loaded.observations[0].observation_text != loaded.interpretations[0].interpretation_text
        assert len(loaded.interpretations) == 1
        assert loaded.interpretations[0].production_concept == "filter-cutoff"
        assert loaded.model_metadata.provider_attestation is None
    finally:
        os.unlink(tmp_path)

    print("[PASS] test_visual_evidence_schema")


def test_replay_reconstructs_production_intent():
    """Reloaded visual bundle → UniversalProductionIntent → ProducerBrain."""
    from serum2.source.visual_evidence import (
        VisualEvidenceBundle, VisualFrameArtifact, VisualObservation,
        VisualInterpretation, VisualModelMetadata,
    )
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest

    # Build a minimal bundle (simulates a persisted VLP-1 episode)
    bundle = VisualEvidenceBundle(
        source_url="https://www.youtube.com/watch?v=k6OBzXdcFtA",
        source_id="yt_k6OBzXdcFtA",
        video_id="k6OBzXdcFtA",
    )
    bundle.frames.append(VisualFrameArtifact(
        frame_id="frame_yt_k6OBzXdcFtA_00045000",
        source_url=bundle.source_url,
        source_id=bundle.source_id,
        video_id=bundle.video_id,
        timestamp_sec=45.0,
        artifact_path="serum2/data/visual_frames/yt_k6OBzXdcFtA/test_frame.jpg",
        artifact_hash="b" * 64,
    ))
    bundle.interpretations.append(VisualInterpretation(
        interpretation_text="The producer reduced filter cutoff to darken the bass.",
        production_concept="filter-cutoff",
        semantic_direction="decrease",
        supporting_frame_ids=["frame_yt_k6OBzXdcFtA_00045000"],
        production_action="darker filter cutoff",
        confidence=0.78,
    ))

    # Reconstruct intent from best interpretation
    brain = ProducerBrain()
    intent = brain._visual_evidence_to_intent(bundle, "What production technique was used?")

    assert intent is not None, "Should produce a valid intent"
    assert intent.target_concept == "filter-cutoff"
    assert intent.semantic_direction is not None

    # Send reconstructed intent to ProducerBrain
    # Use the production_action as the effective intent text
    req = ProducerRequest(
        user_intent=bundle.interpretations[0].production_action,
        mode="EXECUTE",
        visual_mode="NEVER",  # no re-acquisition in replay
    )
    result = brain.execute(req)

    assert result.execution_status != "BRAIN_ERROR", (
        "Brain should not error on valid visual-derived intent"
    )
    # The concept should be resolved (filter-related keywords in intent)
    # Status may be MCP_PLAN_READY, EXECUTED, or REFUSED (no contract) — all valid
    # The key is: the intent was processable
    assert result.resolved_concept is not None, (
        "Brain should resolve a concept from visual-derived intent"
    )

    print("[PASS] test_replay_reconstructs_production_intent")
    print("       concept=%s route=%s status=%s" % (
        result.resolved_concept, result.execution_route, result.execution_status
    ))


def test_transcript_sufficiency_check():
    """_check_transcript_sufficiency detects 1-item store as INSUFFICIENT."""
    from serum2.producer.producer_brain import ProducerBrain
    brain = ProducerBrain()

    # VLP-1 source: known to have only 1 item (punctuation bug)
    check = brain._check_transcript_sufficiency(
        "yt_k6OBzXdcFtA",
        "dark bass filter"
    )
    assert check.status in ("INSUFFICIENT_OPERATIONAL", "UNAVAILABLE", "SUFFICIENT"), (
        "Status must be one of the three defined values"
    )
    # For the VLP-1 video we know there's 1 item
    if check.evidence_item_count <= 1:
        assert check.status == "INSUFFICIENT_OPERATIONAL", (
            "1-item store must be INSUFFICIENT_OPERATIONAL"
        )

    print("[PASS] test_transcript_sufficiency_check: status=%s items=%d" % (
        check.status, check.evidence_item_count
    ))


def test_experience_record_has_visual_fields():
    """ProductionExperienceRecord has visual_evidence and transcript_sufficiency fields."""
    from serum2.server.experience_record import ProductionExperienceRecord

    rec = ProductionExperienceRecord(
        experience_id="exp_test_vlp1",
        run_id="test_vlp1",
        visual_evidence={"frames": [], "observations": [], "interpretations": []},
        transcript_sufficiency={"status": "INSUFFICIENT_OPERATIONAL", "reason": "test"},
    )
    d = rec.to_dict()
    assert "visual_evidence" in d
    assert "transcript_sufficiency" in d
    assert d["transcript_sufficiency"]["status"] == "INSUFFICIENT_OPERATIONAL"
    print("[PASS] test_experience_record_has_visual_fields")


def test_unknown_destination_cannot_become_executable_target():
    """An unresolved modulation destination must not become an executable
    target through genre/title convention, hardcoded fallback, or semantic
    guessing.

    Regression for the k6OBzXdcFtA VLP-1 case: the interpretation genuinely
    observed custom LFO/modulation-shape editing, but the destination
    parameter was not legible in the source frames. The (invalidated)
    UNSUPPORTED_INFERENCE episode inferred target_concept='filter-cutoff'
    from the video's title ("...Dubstep GROWLS...") rather than from visible
    evidence. This must never happen again, at two independent points:

    1. _visual_evidence_to_intent() must not propagate a concept when the
       interpretation's production_concept is empty (destination unknown).
    2. execute_producer_request() must REFUSE — not guess a route — when
       given intent text that only contains genre/title language and no
       supported-concept keyword, even though 'dubstep'/'growl' language is
       thematically adjacent to filter-cutoff/dark bass sound design.
    """
    from serum2.source.visual_evidence import (
        VisualEvidenceBundle, VisualFrameArtifact, VisualObservation,
        VisualInterpretation,
    )
    from serum2.producer.producer_brain import (
        ProducerBrain, ProducerRequest, ExecutionRoute,
    )

    bundle = VisualEvidenceBundle(
        source_url="https://www.youtube.com/watch?v=k6OBzXdcFtA",
        source_id="yt_a16958bfb5bc",
        video_id="k6OBzXdcFtA",
    )
    bundle.frames.append(VisualFrameArtifact(
        frame_id="frame_yt_a16958bfb5bc_00133446",
        source_url=bundle.source_url,
        source_id=bundle.source_id,
        video_id=bundle.video_id,
        timestamp_sec=133.446,
        artifact_path="serum2/data/visual_frames/yt_a16958bfb5bc/frame_yt_a16958bfb5bc_00133446.jpg",
        artifact_hash="114dc00e6aa2a463d6c8525604d8c783700a7c6f9e9d50d22c470fc687731998",
    ))
    bundle.observations.append(VisualObservation(
        frame_id="frame_yt_a16958bfb5bc_00133446",
        timestamp_sec=133.446,
        observation_text=(
            "The modulation shape-editor pad shows a jagged, multi-segment "
            "zigzag curve."
        ),
        observable_type="waveform_display",
        ui_element="modulation_shape_editor",
        confidence=0.85,
    ))
    # The interpretation text itself contains genre/title language (as the
    # real one did) precisely to prove that its mere presence in prose does
    # not leak through — only an explicit production_concept would route.
    bundle.interpretations.append(VisualInterpretation(
        interpretation_text=(
            "Custom LFO/modulation-shape design, as demonstrated in a "
            "'How to Make Dubstep GROWLS in SERUM 2' tutorial. Destination "
            "unknown — not legible at source resolution."
        ),
        production_concept="",   # destination unknown — deliberately unset
        semantic_direction="",   # deliberately unset
        supporting_frame_ids=["frame_yt_a16958bfb5bc_00133446"],
        confidence=0.0,
        production_action=None,
    ))

    brain = ProducerBrain()

    # 1. The bridge must not propagate a concept for an unresolved destination.
    intent = brain._visual_evidence_to_intent(bundle, "dubstep growl bass tutorial")
    assert intent is not None, "bridge should still return an intent object"
    assert not intent.target_concept, (
        "target_concept must be falsy when the interpretation's "
        "production_concept is unset — got %r" % intent.target_concept
    )

    # 2. Genre/title-only text must REFUSE at the brain, not guess a route.
    #    No parameter keyword (e.g. 'cutoff', 'darker') is present — only
    #    genre words that are thematically adjacent to filter-cutoff.
    req = ProducerRequest(
        user_intent="dubstep growl bass tutorial",
        mode="EXECUTE",
        visual_mode="NEVER",
    )
    result = brain.execute(req)

    assert result.resolved_concept != "filter-cutoff", (
        "genre language must not resolve to filter-cutoff by guessing"
    )
    assert result.admitted is not True, (
        "an unresolved/guessed concept must never be admitted"
    )
    assert result.execution_route != ExecutionRoute.ABLETON_MCP.value, (
        "genre language must not be routed to Ableton MCP execution"
    )
    assert result.execution_status.startswith("REFUSED_"), (
        "expected a REFUSED_* status for unmapped genre text, got %r"
        % result.execution_status
    )

    print("[PASS] test_unknown_destination_cannot_become_executable_target")
    print("       target_concept=%r resolved_concept=%r status=%s" % (
        intent.target_concept, result.resolved_concept, result.execution_status
    ))


if __name__ == "__main__":
    test_visual_evidence_schema()
    test_replay_reconstructs_production_intent()
    test_transcript_sufficiency_check()
    test_experience_record_has_visual_fields()
    test_unknown_destination_cannot_become_executable_target()
    print("\nAll VLP-1 replay tests passed.")
