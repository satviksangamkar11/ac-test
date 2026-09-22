# youtube_to_serum — Execution Plan

**Status:** Folder structure + validation complete. Implementation blocked pending Phase 4 reference reproduction gate.

## Pipeline (NOT YET IMPLEMENTED)

1. **Video Acquisition** → `serum2/source/fetch_youtube.py`
   - Input: YouTube URL
   - Action: yt-dlp download → local video file
   - Output: video.mp4 + metadata (sha256, duration, fps)

2. **Transcript Extraction** → `serum2/source/youtube_transcript_resolver.py`
   - Input: video_id
   - Action: youtube-transcript-api + fallback whisper
   - Output: timestamped transcript segments

3. **Frame Acquisition** → `serum2/source/acquire_visual_evidence.py`
   - Input: video.mp4 + sampling strategy
   - Action: ffmpeg frame extraction every 45 sec (8 max frames)
   - Output: frame PNG files + hash provenance

4. **Expected Inventory** → `serum2/producer/expected_inventory.py`
   - Input: transcript segments + reference episode context
   - Action: Atlas-driven semantic expectation pruning
   - Output: EPISODE_EXPECTED_SET (subset of 1,136 controls relevant to this video)

5. **Visual Evidence** → `serum2/source/acquire_visual_evidence.py`
   - Input: frames + OCR model
   - Action: Computer vision + text extraction
   - Output: observed parameter values, UI state, visible labels

6. **State Ledger** → `serum2/evidence/record.py` + observation
   - Input: transcript + frames + visual evidence
   - Action: Build canonical observation ledger
   - Output: TERMINAL_OBSERVATION_SET with explicit outcomes per control

7. **Producer Brain** → `serum2/producer/producer_brain.py`
   - Input: EPISODE_EXPECTED_SET + TERMINAL_OBSERVATION_SET + transcript
   - Action: Semantic reasoning + skill/capability matching
   - Output: ProducerResult with admitted operations

8. **Capability Resolution** → `serum2/knowledge/step_6_6_capability_resolution.py`
   - Input: proposed_operation + contract_registry
   - Action: Map universal semantics to Serum control contracts
   - Output: CapabilityResolution (RESOLVED or NOT_FOUND)

9. **Admission** → `serum2/evidence/admission.py`
   - Input: CapabilityResolution + prerequisites
   - Action: Authority gate check (verified contracts only)
   - Output: AdmissionResult (ADMITTED or REFUSED_*)

10. **Serum Preset Generation** → `vendor/serum-mcp/` tools
    - Input: admitted operations → PresetSpec
    - Action: serum-mcp generate_preset() → .SerumPreset file
    - Output: reference_reproduction.SerumPreset (Serum 2.0.21 binary)

11. **Live Readback Verification** → Serum 2.0.21 GUI
    - Input: .SerumPreset file
    - Action: Load in Serum plugin UI → read actual control values
    - Output: LIVE_READBACK_VERIFIED terminal state

## Known Blockers

- **Phase 4 Reference Reproduction Gate:** Episode-specific expected set reduction must be validated (ATLAS_UNIVERSE → EPISODE_EXPECTED_SET)
- **Fallback Transcription:** If youtube-transcript-api unavailable, fallback_transcribe() required (not yet implemented)
- **OCR Model Selection:** Vision model for frame analysis not yet specified
- **Calibration Dependencies:** Slider calibration (P3.5) may affect frame interpretation accuracy

## External Runtime Requirements

```bash
pip install yt-dlp youtube-transcript-api
# Also required: ffmpeg, ffprobe (system binaries)
```

## Entry Point (When Ready)

```python
from serum2.source.fetch_youtube import download_youtube_video
from serum2.producer.expected_inventory import build_episode_expected_set
from serum2.producer.producer_brain import execute_producer_request

# video_url = "https://www.youtube.com/watch?v=..."
# 1. Download + transcript
# 2. Acquire frames
# 3. Build expected set
# 4. Execute producer_brain
# 5. Generate preset
# 6. Load in Serum → verify
```

## Testing Strategy

- **Smoke tests:** 6/6 passing (imports + schema loads)
- **Unit tests:** Use external pytest on serum2/producer/test_*.py
- **Integration:** End-to-end YouTube→preset on reference episode (HEEGN1Xl5o4 or equivalent)
