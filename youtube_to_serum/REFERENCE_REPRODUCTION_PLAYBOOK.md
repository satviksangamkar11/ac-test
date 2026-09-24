# REFERENCE REPRODUCTION PLAYBOOK

## Purpose

Canonical implementation playbook for the Reference-to-Serum Reproduction system.

Primary target:

YouTube/reference video -> complete multimodal evidence -> complete reference knowledge -> Producer Brain reasoning/retrieval -> typed operations -> target/Atlas resolution -> capability resolution -> admission -> authorized execution -> serum-mcp -> .SerumPreset -> file readback -> live Serum UI verification -> forensic documentation.

Ableton and 16-bar production remain frozen until Reference-to-Serum reproduction reaches its closure gate.

---

# 0. NON-NEGOTIABLE ARCHITECTURE

## Perception

Answers: What is visibly/audibly present in the reference?

Inputs:
- video frames
- audio
- transcript
- OCR
- temporal context

Output:
- evidence observations only

## Reference Knowledge

Answers: What did the complete reference contain, and what do we know about it?

It preserves:
- executable observations
- non-executable observations
- unreadable observations
- conflicting observations
- ambiguous observations
- unsupported parameters
- temporal changes
- transcript facts
- visual facts
- provenance

Nothing is dropped merely because execution is unavailable.

## Producer Brain

Answers: What does the accumulated reference knowledge mean, and what relevant information should be retrieved/reasoned over?

Brain may:
- retrieve
- interpret
- correlate
- summarize
- explain
- propose typed operations

Brain may NOT:
- grant authority
- bypass Atlas resolution
- bypass capability resolution
- bypass admission
- invent missing reference values
- directly mutate Serum

## Authority / Execution

Canonical authority chain:

Atlas/Target -> Capability -> Admission -> Authorized Operation -> Generic Compiler -> serum-mcp

## Verification

Answers:
- Did the generated preset contain the requested state?
- Did actual Serum show the same state?

Verification remains independent from generation.

---

# 1. CURRENT PROJECT STATE

Repository:
satviksangamkar11/ac-test

Current hardened branch:
generic-binding-contracts

Latest pushed commit:
76528dc67a1208408b599e8f9cd2140ad7e5ca7a

Previous hardening checkpoint:
bf5c7e01017a5b99f4549f9e61dad136825bf82c

Reported project suite:
948 passed, 3 skipped

Generic binding evidence loader:
implemented and pushed

Schema-driven value-domain typing:
implemented and pushed

Binding evidence artifacts:
18 pushed

bridge_index:
unchanged

find_contract:
unchanged

Latest trial:
15 operations compiled

Trial file readback:
15 matched (10 exact, 5 normalized)

Current unresolved trial boundary:
2 INCOMPATIBLE_OPERATION rows

Live UI verification:
13 working controls are being verified; final verification run must establish the final proof state.

Trial proof level before final UI run:
FILE_READBACK_VERIFIED_ONLY

Trial coverage:
PARTIAL

Important:
The verified production/reference preset and final_report must not be overwritten by a trial.

Product-branch fact:
The isolated youtube_to_serum product tree is on phase-4-youtube-to-serum-product at commit cd697c4ccba4a942884ca46a165ccfb2880ab280. It is not currently present as a top-level product folder on generic-binding-contracts. Integration must be deliberate.

---

# 2. CONTEXT-PRESERVATION PROTOCOL

Do not depend on chat history as the sole project memory.

Maintain three persistent layers.

## 2.1 Canonical playbook

File:
REFERENCE_REPRODUCTION_PLAYBOOK.md

Contains:
- architecture
- invariants
- sequence
- gates
- remaining work
- design decisions
- research basis

Change it only when architecture, sequencing, or gates change.

## 2.2 Current state snapshot

File:
PROJECT_STATE.md

Contains:
- current branch and commit
- current phase
- completed gates
- active blocker
- latest test count
- latest run/proof/coverage
- current changed files
- exact next action
- known unresolved issues

Update after every meaningful implementation, test, or research turn.

## 2.3 Decision log

File:
DECISION_LOG.md

Append architecture-changing decisions such as:
- every frame must receive an analysis record
- transcript is evidence, not authority
- non-executable parameters remain in knowledge and forensic documentation
- Brain cannot authorize
- memory cannot authorize
- implicit evidence loading is forbidden
- no parameter-specific execution branches
- serum-mcp remains the Serum execution backend
- trial artifacts never replace verified artifacts

## 2.4 Every future project prompt

Before acting:
1. Read PROJECT_STATE.md.
2. Read the relevant playbook section.
3. Inspect the actual repository/run evidence when implementation facts matter.
4. Perform the work.
5. Run sufficient tests.
6. Update PROJECT_STATE.md.
7. Update this playbook when the plan/gates changed.
8. Append DECISION_LOG.md when architecture changed.
9. Record exact commit/run/test/proof information.
10. Never replace verified state with an assumption.

This makes project context persistent rather than conversational.

---

# 3. FINAL REFERENCE PIPELINE

YouTube
-> source acquisition
-> complete frame decode
-> local visual analysis
-> local ASR
-> OCR / UI detail extraction
-> temporal evidence fusion
-> complete Reference Knowledge
-> Producer Brain
-> typed operations
-> target / Atlas resolution
-> capability resolution
-> admission
-> authorized operation set
-> generic compiler
-> serum-mcp
-> .SerumPreset
-> file readback
-> real Serum load
-> DIRECT_UI readback
-> normalized comparison
-> proof/coverage
-> forensic report
-> knowledge/experience products

The Brain sees complete reference knowledge.
The Brain does not own execution authority.

---

# 4. STEP 1 — CLOSE CURRENT 15-OPERATION TRIAL

## 4.1 Diagnose the two INCOMPATIBLE_OPERATION rows first

Known examples:
- oscA.enabled
- filter1.enabled

Reported issue:
operand_kind mismatch between enum-like field representation and numeric operation family.

Required:
- inspect ledger operation
- inspect derived operation family/type
- inspect Atlas control type
- inspect serum-mcp schema field type
- inspect admission/compiler expectations
- determine whether refusal is correct or generic type mapping is wrong
- do not add a parameter-specific exception

Gate:
Each row has a complete terminal explanation and no silent fallback.

## 4.2 Finish live UI verification

Use the separate trial preset.

For each working control:
1. load exact generated preset into Serum
2. capture actual UI value
3. preserve raw displayed representation
4. normalize only for comparison
5. compare against ledger expected value
6. classify exact or normalized match
7. store evidence reference

Do not treat serum-mcp describe_preset as equivalent to DIRECT_UI proof.

Gate:
LIVE_UI_VERIFIED for the verified subset.

Do not set reference_verified=true while coverage is PARTIAL.

## 4.3 Freeze the trial result

Persist:
- preset path
- preset SHA
- file comparison
- UI comparison
- exact/normalized counts
- incompatible rows
- proof level
- coverage
- replay pins

---

# 5. STEP 2 — INTEGRATE THE PRODUCT FOLDER WITH THE HARDENED CORE

The isolated youtube_to_serum branch is an older/product-focused tree. Do not blindly replace hardened core modules.

Process:
1. establish generic-binding-contracts as the canonical authority core
2. import the product shell/source layer
3. compare duplicate serum2 files
4. retain later hardening when both versions implement the same responsibility
5. keep acquisition/UI files that are additive
6. eliminate duplicate authorization routes
7. run imports and tests
8. document intentional differences

Gate:
One coherent source of truth for execution and authority.

---

# 6. STEP 3 — SOURCE ACQUISITION

Input:
- YouTube URL or local reference video

Produce:
- video ID
- source URL
- retrieval timestamp
- local file
- source byte SHA-256
- duration
- FPS
- width/height
- audio metadata
- decoder/tool versions

Source acquisition is evidence preparation only.

Gate:
The exact source bytes are identifiable and replayable.

---

# 7. STEP 4 — WHOLE-VIDEO FRAME COVERAGE

This is mandatory.

Requirement:
Every video frame must receive an analysis record.

The older product strategy of sparse extraction such as every 45 seconds / 8 maximum frames is not sufficient for final production.

## Optimize computation without losing coverage

Use:

decode every frame
-> assign frame index and timestamp
-> batch adjacent frames into model requests
-> analyze every frame
-> emit one result record per frame

Scene detection may organize the timeline but must not silently discard frames.

Use scene detection for:
- boundaries
- grouping
- temporal context
- prioritization of detail analysis

It is not an evidence-dropping mechanism.

## Every-frame record

Minimum:
- source SHA
- frame index
- timestamp
- frame hash
- model identity
- model revision/checksum when available
- prompt/template hash
- inference configuration hash
- processing status
- observation IDs

Frame terminal statuses can include:
- ANALYZED_WITH_OBSERVATIONS
- ANALYZED_NO_RELEVANT_SERUM_STATE
- ANALYZED_UNREADABLE
- ANALYSIS_ERROR

The key invariant is that no frame is absent from the accounting set.

## Full frame and crops

Each frame gets full-frame visual analysis.

Optional detail crops may then be created for:
- tiny parameter text
- hover tooltip
- mode labels
- dense UI regions

Crops supplement full-frame evidence; they do not replace it.

---

# 8. STEP 5 — LOCAL TRANSCRIPT / ASR

Primary benchmark candidate:
Whisper large-v3-turbo.

Pipeline:

video audio
-> local ASR
-> timestamped transcript
-> transcript evidence store

Record:
- audio SHA
- ASR model
- model revision
- language handling
- timestamps
- raw transcript
- normalized segments

Transcript is supporting evidence.

Example:
Transcript says 500 ms.
UI shows 600 ms.

Correct result:
conflict record.

Incorrect result:
transcript automatically overrides UI.

Gate:
Transcript can be regenerated from the same audio source.

---

# 9. STEP 6 — LOCAL VIDEO UNDERSTANDING

Use a local VLM.

Recommended benchmark family:
Qwen3-VL.

Recommended exhaustive first-pass candidate:
Qwen3-VL-8B.

Escalation:
a larger Qwen3-VL model for uncertain frames when hardware permits.

Serving:
benchmark direct Transformers and vLLM.

Qwen3-VL provides local image/video inference paths, long-context video understanding, OCR capabilities, and temporal/timestamp-oriented modeling.

## VLM task

Do NOT ask:
How do I create this preset?

Ask:
What is visibly present in this frame/window?

Output structured observations:
- frame reference
- timestamp
- visible module
- visible control/label
- observed value
- units
- mode/state
- visual region
- readability
- uncertainty/confidence
- temporal context
- evidence text

The VLM is an observer, not an executor.

## No hallucinated values

If the UI shows a value:
record the value.

If the value is obscured:
record UNREADABLE.

Never:
UNREADABLE -> invented numeric value.

---

# 10. STEP 7 — SPECIALIZED OCR

Use VLM vision plus specialized local OCR where text is small or difficult.

Candidate:
PP-OCRv5.

Use OCR for:
- parameter labels
- tooltip values
- units
- mode names
- selected menu values
- tiny text

Preserve:
- raw OCR output
- crop/frame reference
- OCR model/version
- normalized interpretation

OCR is evidence, not authority.

---

# 11. STEP 8 — TEMPORAL EVIDENCE FUSION

Inputs:
- VLM frame observations
- OCR
- transcript
- nearby frames
- UI geometry
- Atlas context

Output:
REFERENCE_OBSERVATION_SET

Every normalized fact retains source references.

Example:

oscA.octave = -1

Sources:
- frame A VLM
- frame B OCR
- frame C VLM
- transcript cue

Do not call this exact merely because multiple weak sources agree.

Possible statuses:
- supported
- corroborated
- conflicting
- ambiguous
- unreadable

Temporal reasoning should detect transitions.

Example:

frame 1000: octave 0
frame 1010: octave 0
frame 1020: control changed
frame 1030: octave -1
frame 1040: octave -1

Derived state transition:
0 -> -1

Raw observations remain stored.

---

# 12. STEP 9 — COMPLETE REFERENCE KNOWLEDGE

Reference Knowledge is the full factual representation of the video.

Suggested layers:

Raw Evidence
-> immutable observations

Normalized Observations
-> canonical target/value/timestamp representations

Temporal State
-> state intervals/transitions

Reference Knowledge Items
-> Brain-consumable facts with evidence links

Execution Projection
-> strictly derived subset that may be considered for execution

Critical invariant:

Reference Knowledge != Execution Projection

An item may be known but unexecutable.

---

# 13. STEP 10 — NON-EXECUTABLE PARAMETERS

Every observed but non-executable parameter remains in the knowledge system and is written to forensic documentation.

Example:

LFO1 mode = Chaos: Lorenz

Knowledge:
PRESENT

Execution:
BLOCKED

Reason:
enum alias/value contract unresolved

Another:

Control present, value obscured

Knowledge:
CONTROL PRESENT

Value:
UNREADABLE

Execution:
NOT ATTEMPTED

Another:

Value known, no serum-mcp capability

Knowledge:
PRESENT

Execution:
NO_CAPABILITY

Never produce "no items documented" when items exist.

---

# 14. STEP 11 — PRODUCER BRAIN

Brain receives complete reference knowledge.

Input:
- all visual observations
- transcript
- temporal transitions
- unresolved items
- unsupported items
- prior verified experiences
- source context

Brain can:
- retrieve
- explain
- correlate
- summarize
- reason
- identify missing information
- propose typed operations

Brain cannot:
- authorize
- mutate Serum
- fabricate evidence
- invent missing values
- bypass contracts
- bypass admission

Canonical chain:

Brain
-> typed operation
-> target/Atlas
-> capability
-> admission

---

# 15. STEP 12 — KNOWLEDGE COVERAGE RECONCILIATION

Build a reconciliation gate between all observation-derived knowledge and execution.

Every reference item must have exactly one terminal disposition:

- executable
- non-executable
- unresolved
- unreadable
- conflicting
- unsupported
- irrelevant/non-Serum

No observation is silently discarded.

Coverage invariant:

ALL_OBSERVATIONS
=
CLASSIFIED_OBSERVATIONS

The classified output may contain many categories, but no item disappears.

---

# 16. STEP 13 — ATLAS / TARGET RESOLUTION

Use the existing Atlas and target-resolution mechanisms.

Do not introduce video-specific hardcoded mappings.

Observed semantic identity
-> Atlas target

Unknown identity
-> unresolved

Ambiguous identity
-> unresolved / investigation

Wrong instance
-> not covered by that contract

Keep bridge_index/find_contract universal.

---

# 17. STEP 14 — CAPABILITY RESOLUTION

Question:
Is there a verified capability for this typed operation?

Inputs:
- current contracts
- explicitly loaded evidence-derived contracts
- current Serum epoch
- schema/domain evidence
- body-path coverage

Do not infer authority from:
- Brain
- VLM
- transcript
- audio similarity
- candidate accessor
- memory
- successful-looking preset

---

# 18. STEP 15 — GENERIC EVIDENCE-DERIVED CONTRACTS

Current loader responsibilities:
1. discover evidence files
2. validate
3. validate value domain
4. verify Serum binary SHA
5. run ClaimEngine
6. run build_contract
7. require evidence-derived binding
8. reject duplicate targets
9. expose diagnostics

Diagnostics:
- loaded
- rejected_invalid_evidence
- rejected_no_binding
- rejected_epoch
- rejected_contract

Loading is explicit:
binding_evidence_dir must be named.

Never silently widen authority by discovering a directory implicitly.

---

# 19. STEP 16 — VALUE DOMAIN

Current generic rule:

valid mutation domain = Atlas bounds intersect serum-mcp schema bounds

Type:
- toggle -> bool
- integer schema/Atlas -> integer
- float schema -> float
- unresolved enum domain -> QUALIFICATION_BLOCKED until alias/value domain is established

Already fixed:
- oscA.unison uses integer values
- oscA.octave uses integer values
- oscA.semitone is clamped by schema intersection

Do not create control-specific exceptions.

---

# 20. STEP 17 — ADMISSION

For each derived operation:
1. terminal operation classification exists
2. target resolves
3. capability resolves
4. instance/body-path scope matches
5. epoch matches
6. prerequisites satisfy contract
7. admission returns explicit terminal status

No PENDING/NOT_EVALUATED operation may escape the admission boundary.

---

# 21. STEP 18 — GENERIC COMPILER

Only authorized operations reach the compiler.

Compiler must remain universal.

Never introduce:
- control-specific if/else
- fixed constants for a named Serum parameter
- semantic-ID switches
- Brain-provided execution shortcuts

Compiler consumes authorized data:
- contract
- binding
- target path
- operation type
- validated operand

---

# 22. STEP 19 — SERUM-MCP

All Serum file execution uses serum-mcp.

Production path:
generic compiler -> serum-mcp

Do not revive old Ableton/DawDreamer qualification harnesses as canonical execution.

serum-mcp performs:
- preset generation
- supported preset edits
- preset description/readback

It does not decide authority.

---

# 23. STEP 20 — FILE READBACK

After preset creation:
generated preset
-> read back via preset representation
-> compare against authorized expected state

Classify:
- exact
- normalized
- mismatch
- missing
- extra/collateral

File readback is not live UI proof.

---

# 24. STEP 21 — LIVE SERUM UI VERIFICATION

For UI proof:
1. load the exact generated preset
2. verify plugin context
3. read actual UI
4. preserve raw UI values
5. normalize for comparison
6. compare to expected reference
7. store evidence
8. classify exact/normalized/mismatch/not observed

Direct UI evidence must retain provenance tied to:
- run
- preset
- Serum epoch
- expected control
- actual observation

---

# 25. STEP 22 — PROOF VS COVERAGE

proof_level:
How strongly the reproduced subset was verified.

coverage_status:
How much of the reference was reproduced.

Examples:
LIVE_UI_VERIFIED + PARTIAL
= subset verified, reference incomplete.

FILE_READBACK_VERIFIED_ONLY + PARTIAL
= file verified for subset, not live-proven and not complete.

Only:
LIVE_UI_VERIFIED + COMPLETE

can yield:
reference_verified = true

---

# 26. STEP 23 — FORENSIC DOCUMENT

Generate automatically.

Required sections:
1. source identity
2. source hashes
3. frame coverage
4. transcript coverage
5. VLM model/revision
6. OCR model/revision
7. evidence fusion
8. knowledge counts
9. all observed controls
10. executable controls
11. non-executable controls
12. unreadable controls
13. conflicts
14. unsupported controls
15. admitted operations
16. refused operations
17. compiled operations
18. file readback
19. UI readback
20. proof level
21. coverage status
22. reference_verified
23. replay pins
24. unresolved issues
25. next action

The document is generated from machine-readable run artifacts, not hand-authored completion flags.

---

# 27. STEP 24 — WEB UI

The UI is a thin shell over the canonical orchestrator.

Input:
YouTube URL

Display:
- source acquisition
- transcript progress
- frame-analysis progress
- knowledge progress
- Brain progress
- admission counts
- compilation counts
- verification
- forensic documentation

The UI cannot:
- construct a hardcoded preset
- choose authority
- override admission
- fabricate observations

---

# 28. STEP 25 — SINGLE COMMAND

Final target:
one command/API call runs the complete pipeline.

Conceptually:

source
-> transcript
-> all frames
-> VLM
-> OCR
-> temporal fusion
-> knowledge
-> Brain
-> operations
-> resolution
-> admission
-> compiler
-> serum-mcp
-> file verification
-> UI verification
-> forensic report

Each stage remains independently testable.

---

# 29. STEP 26 — REPLAY PINS

Each run pins:
- source SHA
- video metadata
- transcript SHA
- frame manifest SHA
- VLM model/revision
- VLM prompt hash
- OCR model/revision
- evidence schema version
- Atlas hash/version
- schema fingerprint
- binding evidence identity
- execution epoch
- Serum binary SHA
- contract identities
- compiler SHA
- serum-mcp source/version
- preset SHA

A replay must explain why the exact execution set was authorized.

---

# 30. STEP 27 — MEMORY / KNOWLEDGE PRODUCT

Two useful memory scopes:

Reference memory:
- per-video observations
- timeline
- parameters
- evidence
- unresolved items
- execution outcomes

Production memory:
- verified experience
- successful binding evidence
- known failure modes
- prior verified operations

Memory improves retrieval/reasoning only.

Memory cannot grant authority.

---

# 31. STEP 28 — EXPERIENCE PROMOTION

Promote only verified products.

VerifiedOperationEvidence:
subset with live UI proof.

VerifiedReferenceEpisode:
only when proof is LIVE_UI_VERIFIED and coverage is COMPLETE.

Never learn authoritative execution from:
- transcript alone
- VLM guesses
- file self-comparison alone
- unsupported controls
- rejected operations
- Brain assertions

---

# 32. STEP 29 — ERROR TAXONOMY

Every failure receives a terminal category.

Reference:
- unreadable
- ambiguous
- conflicting
- non-Serum
- unsupported visual element

Knowledge:
- unresolved identity
- unresolved value
- conflicting evidence
- insufficient evidence

Execution:
- no capability
- scope would expand
- epoch mismatch
- incompatible operation
- admission refused
- compiler refusal
- serum-mcp refusal

Verification:
- file mismatch
- UI mismatch
- not observed
- normalization mismatch
- verification unavailable

No silent fallback.

---

# 33. STEP 30 — PERFORMANCE

Correctness comes before optimization.

Use:
- streaming video decode
- batched model inference
- persistent frame manifest
- frame hashing
- OCR caching
- VLM output caching
- transcript caching
- parallel CPU preprocessing
- GPU batching

Cache keys must include model/prompt/source identity.

For local VLM:
- small model for exhaustive pass
- larger model for uncertainty escalation
- temporal windows with overlap
- full-frame analysis plus detail crops
- benchmark direct local inference versus vLLM

Do not enable token/frame reduction in authoritative exhaustive mode if it causes required frames/details to disappear from the evidence contract.

---

# 34. STEP 31 — MODEL BENCHMARK

Build fixed benchmark fixtures containing:
- Serum screenshots
- short Serum videos
- hover-only values
- tiny text
- toggles
- integers
- floats
- enum/modes
- rapid changes
- unchanged frames
- transcript/UI contradictions

Measure:
- frame coverage
- parameter precision
- parameter recall
- false numeric rate
- enum hallucination rate
- unreadable accuracy
- timestamp accuracy
- temporal transition accuracy
- OCR accuracy
- throughput
- latency
- memory/VRAM

The benchmark must reject the historical weak criterion of "PASS because output contains UNREADABLE".

---

# 35. STEP 32 — TEST MATRIX

Unit:
- frame schema
- evidence schema
- provenance
- domain validation
- transcript parsing
- normalization
- knowledge ingestion
- coverage conservation
- evidence fusion
- temporal reasoning
- non-executable classification
- forensic rendering

Regression/property:
- arbitrary candidate IDs
- arbitrary instances
- wrong instance
- duplicate target
- wrong epoch
- malformed evidence
- missing domain
- type violations
- conflicting evidence
- unreadable evidence
- Brain cannot authorize
- memory cannot authorize
- transcript cannot authorize

Integration:
video fixture -> all frame records -> knowledge -> Brain -> admission -> serum-mcp -> file readback

Live:
generated preset -> real Serum -> DIRECT_UI -> normalized comparison

---

# 36. STEP 33 — AUDIT ITEMS TO KEEP OPEN

The generic loader does not automatically solve all historical audit findings.

Keep tracking:
- forgeable AuthorizedOperation fields
- parallel legacy compiler authorization
- per-target contract-registry branches
- weak UI-readback provenance binding
- legacy Brain authority shortcuts
- unsafe authority artifact loading
- fail-open skills/evidence
- hand-authored verification
- hardcoded epoch inference
- route taxonomy drift
- evidence/learning gate weaknesses
- silent fallbacks
- clean-clone reproducibility

Every future fix must preserve:
reference facts != logic != evidence != authority

---

# 37. STEP 34 — CLEAN CLONE

Final production gate:
1. fresh clone
2. install dependencies
3. install/verify local models
4. verify serum-mcp
5. verify Serum environment
6. run tests
7. run fixed reference fixture
8. reproduce evidence
9. compile preset
10. file readback
11. live UI verification
12. forensic report
13. replay

No hidden reliance on:
- personal paths
- untracked files
- stale run artifacts
- shell-specific formatting
- local-only authority artifacts

---

# 38. STEP 35 — FINAL REFERENCE CLOSURE

Closure requires:

Coverage:
Every relevant frame has an analysis terminal.

Knowledge:
Every observed Serum parameter is represented or explicitly classified.

Execution disposition:
Every knowledge item has an outcome.

Authority:
Every executable operation passed canonical resolution/admission.

Compilation:
Every admitted operation has a terminal compiler outcome.

File verification:
Authorized state matches generated preset readback.

Live UI:
Required executable state matches actual Serum UI.

Forensics:
Non-executable state is documented.

Provenance:
All source/model/schema/contract/compiler/Serum/preset identities are pinned.

Replay:
The run can be reproduced without chat history.

Only then:
reference_verified = true

---

# 39. OPTIMIZED IMPLEMENTATION ORDER

Phase A — Current authoritative reproduction

## Phase A status (2026-09-24)

- Phase A.1 (diagnose + fix the boolean operand_kind boundary): **COMPLETE**. Generic fix required two parts: op_operand() TOGGLE→boolean (prior commit) AND capability_contract._mutation_value_kind() bool→MUTATE_BOOLEAN (this session) — the contract-side classification was the second, previously-missed half. See DECISION_LOG.md 2026-09-24 entry.
- Phase A.2 (rerun the current trial with the fix, new trial directory, explicit binding_evidence_dir): **COMPLETE**. Trial `qUNIEASFZSs_trial2_boolfix` — 15 admitted/compiled, oscA.enabled and filter1.enabled both ADMITTED (previously INCOMPATIBLE_OPERATION).
- Phase A.3 (file readback + live Serum UI verification): **COMPLETE, result VERIFICATION_BLOCKED**. File readback 10 exact/5 normalized, 0 mismatches. Live Serum UI readback (real: preset loaded into the running Serum 2 plugin in Ableton, read via screenshot of the actual GUI) — 10 exact/4 normalized/**1 MISMATCH** (`env2.sustain`, unrelated to the boolean fix). Both target rows (oscA.enabled, filter1.enabled) verified UI_VERIFIED_EXACT.
- Phase A.4 (freeze trial state/replay artifacts): **COMPLETE**. Preset, forensic report, replay pins, and PROJECT_STATE.md all frozen under `qUNIEASFZSs_trial2_boolfix/`; the prior verified `qUNIEASFZSs/` trial was not touched.
- Percent display-curve gate: **COMPLETE**. `%` → 0..1 conversion now uses the target field's declared power-curve exponent (`raw = (pct/100)^(1/N)`); undeclared curves are refused. Trial `qUNIEASFZSs_trial3_sustain_curve`: env2.sustain 60% verified live; all 15 compiled ops LIVE_UI_VERIFIED.
- Overall Phase A closure: **NOT COMPLETE** — proof_level LIVE_UI_VERIFIED but coverage_status PARTIAL (2 INCOMPATIBLE_OPERATION, 10 NO_CAPABILITY, 6 EPOCH_MISMATCH, plus non-derived ledger rows). reference_verified = false.

1. diagnose two incompatible operations
2. finish 13-control live UI verification
3. final verification run
4. freeze result
5. update state

Phase B — Product integration
6. integrate youtube_to_serum
7. preserve hardened core
8. remove duplicate execution authority
9. test

Phase C — Complete perception
10. source acquisition
11. exhaustive frame manifest
12. local ASR
13. local VLM
14. OCR
15. temporal fusion

Phase D — Complete knowledge
16. immutable evidence store
17. normalized observations
18. temporal state
19. complete Reference Knowledge
20. coverage reconciliation

Phase E — Brain
21. retrieve complete knowledge
22. interpret
23. correlate
24. generate typed operations
25. enforce no-authority rule

Phase F — Execution
26. target resolution
27. capability resolution
28. evidence-derived contracts
29. admission
30. generic compiler
31. serum-mcp

Phase G — Verification
32. file readback
33. live UI
34. proof/coverage
35. replay pins

Phase H — Productization
36. forensic report
37. non-executable documentation
38. web orchestration
39. one-command entrypoint

Phase I — Production hardening
40. model benchmark
41. performance optimization
42. clean clone
43. replay test
44. closure gate

---

# 40. IMMEDIATE NEXT ACTIONS

Do these before starting broad VLM implementation:

A. Diagnose the 2 INCOMPATIBLE_OPERATION rows.

B. Finish the 13-control live UI verification.

C. Run the final verification with the evidence-derived registry explicitly enabled.

D. Update PROJECT_STATE.md with exact resulting proof/coverage/counts.

E. Integrate the product shell against the hardened core.

F. Build the exhaustive frame-analysis contract.

G. Run local ASR and local VLM benchmarks before choosing the production model/configuration.

H. Implement complete Reference Knowledge ingestion.

I. Wire Producer Brain to complete knowledge, not the executable subset.

J. Implement automatic non-executable forensic documentation.

---

# 41. RESEARCH BASIS

The local-first perception architecture is grounded in current tooling and research.

Qwen3-VL:
- local image/video inference
- long-context video understanding
- temporal/timestamp capabilities
- OCR
- local Transformers and vLLM paths

vLLM:
- multimodal video inputs
- batched inference
- local video serving
- multiple video decoding backends
- optional video-token pruning

Whisper large-v3-turbo:
- local Transformers inference
- 99-language ASR
- faster decoder relative to large-v3

PySceneDetect:
- adaptive scene detection
- useful for temporal organization, not frame dropping

PP-OCRv5:
- specialized OCR for small/text-heavy visual extraction

Agent-memory research:
- durable memory is commonly structured around persistent write/manage/read mechanisms
- for this project that principle maps naturally to PROJECT_STATE + playbook + decision log + reference knowledge
- memory remains separate from authority

---

# 42. HARD RULES FOR EVERY FUTURE IMPLEMENTATION

Never:
- hardcode a Serum parameter into execution logic
- let Brain authorize
- let VLM authorize
- let transcript authorize
- let memory authorize
- drop a parameter because serum-mcp cannot execute it
- treat generated preset as proof
- treat file readback as live UI proof
- treat audio similarity as exact state identity
- convert unreadable into guessed exact values
- implicitly widen the registry
- silently override contracts
- revive old execution harness as canonical Serum execution
- overwrite verified artifacts with trials

Always:
- preserve raw evidence
- preserve provenance
- assign terminal outcomes
- keep complete knowledge
- derive execution as a separate projection
- use Atlas/schema for generic domain rules
- use contracts for authority
- use admission for authorization
- use generic compiler
- use serum-mcp for Serum execution
- verify generated state
- document non-executable observations
- pin replay identity
- update persistent project state after meaningful work

---

# 43. DEFINITION OF DONE

A user provides a YouTube reference.

The system:
1. acquires exact source
2. analyzes every frame
3. transcribes speech locally
4. understands visual state locally
5. preserves all observations
6. builds complete Reference Knowledge
7. lets Brain retrieve/reason over the entire reference
8. classifies every observed parameter
9. documents all non-executable parameters
10. executes only authorized operations
11. generates Serum preset through serum-mcp
12. verifies by file readback
13. verifies in actual Serum UI
14. explains every refusal/unresolved state
15. produces forensic documentation
16. pins replay state
17. reproduces without chat history

At that point the system is an auditable YouTube-to-Serum reproduction engine, not a UI shell around a hardcoded preset.
