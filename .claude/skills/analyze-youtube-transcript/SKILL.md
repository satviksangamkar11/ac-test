---
name: analyze-youtube-transcript
description: Analyze a normalized YouTube tutorial transcript and produce a timestamped visual-inspection cue plan for VLP-1. This skill must identify where visual inspection is useful without deciding canonical production targets, operations, capabilities, routes, or execution.
---

# Purpose

Analyze a timestamped tutorial transcript and produce a deterministic-schema compatible `TranscriptCuePlan` JSON artifact.

The output is an **evidence-acquisition aid only**.

It is **NOT**:
- a Producer Brain
- a semantic target resolver
- an execution planner
- a capability resolver
- an MCP planner
- a parameter mapper
- a control-value mapper

# Input

A normalized transcript JSON artifact containing:
- `source_id`
- `video_id`
- `source_url`
- `language`
- `transcript_sha256`
- `transcript` array with timestamped segments (segment_id, text, start_time_sec, duration)

# Task

Identify transcript regions where visual inspection is likely to establish useful production evidence.

Look for generic linguistic signals such as:
- open, close, click, drag, move, turn
- set, change, select, route, connect
- add, remove, enable, disable, switch
- load, choose, adjust, increase, decrease
- demonstrate, now, next, finally
- UI/application mentions
- control/value mentions
- transition points
- state changes
- explicit action completion statements

**Do NOT convert those mentions into canonical semantic target IDs.**

**Do NOT infer hidden UI state.**

**Do NOT invent parameter values.**

**Do NOT invent timestamps.**

Use only timestamps present in the transcript.

# Timestamp policy

For each useful cue:

1. Use the transcript segment's actual `start_time_sec` and duration.
2. Optionally provide one or more `preferred_timestamps_s` inside the spoken region when the transcript itself provides enough timing information (e.g., "now I'll set the cutoff to 800" → the frame after that statement is complete).
3. Do not claim that a visual change occurred merely because the instructor said it occurred. The frame extraction and Stage-A observation will verify.
4. `verification_reason` must explain why a frame should be inspected (e.g., "The speaker describes a UI action whose completion should be visually checked").

# Output

Return JSON artifact only. No text, no explanation.

**Schema:**

```json
{
  "schema_version": "1.0",
  "runtime": "claude-code",
  "direct_anthropic_sdk": false,
  "api_key_used": false,

  "source_id": "yt_2c5dd65a286a",
  "video_id": "HEEGN1Xl5o4",
  "source_url": "https://www.youtube.com/watch?v=HEEGN1Xl5o4",

  "transcript_sha256": "abc123...",
  "transcript_language": "en",

  "cues": [
    {
      "cue_id": "cue-0001",
      "segment_ids": ["seg-0012", "seg-0013"],
      "start_s": 245.2,
      "end_s": 251.7,
      "preferred_timestamps_s": [247.1, 250.3],
      "kind": "ACTION",
      "focus_terms": [
        "route LFO 1",
        "cutoff"
      ],
      "verification_reason": "The speaker describes a UI routing action whose completion should be visually verified.",
      "confidence": 0.94
    },
    {
      "cue_id": "cue-0002",
      "segment_ids": ["seg-0045"],
      "start_s": 312.1,
      "end_s": 318.9,
      "preferred_timestamps_s": [315.5],
      "kind": "VALUE_MENTION",
      "focus_terms": [
        "resonance",
        "increase"
      ],
      "verification_reason": "The speaker mentions changing a parameter value; inspect the frame to see the actual change.",
      "confidence": 0.87
    }
  ],

  "provenance": {
    "planner": "claude-code",
    "schema_version": "1.0"
  }
}
```

# Hard rules

**Never output:**
- `semantic_target`
- `canonical_target`
- `operation`
- `capability`
- `route`
- `admission`
- `MCP`
- `execution`
- `parameter_value`
- arbitrary control values or names

**Do NOT output claims such as:**
- "The cutoff was changed to 800."
- "The LFO destination is the filter."

**Instead output:**
- "The speaker describes a change involving 'cutoff'; inspect the frame."
- "The speaker mentions routing LFO 1; inspect the frame."

# Reasoning

**Transcript = temporal/context evidence.**
**Frames = visual evidence.**
**Stage-A = visual observation (not inference).**

The transcript tells the system WHERE to look.
The visual extractor and Stage-A tell the system WHAT is actually visible.
The Producer Brain reasons over that evidence.

Your job is the first part only: "WHERE to look."
