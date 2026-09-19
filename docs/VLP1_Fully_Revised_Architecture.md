# Audited Multimodal Producer Architecture
## VLP-1 — Frozen Canonical Architecture v1.0: Boundaries, State Model, and Verification Contract

**Document status:** FROZEN — VLP-1 Canonical Architecture v1.0
**Freeze intent:** Architecture boundaries are frozen; implementation may continue only within these boundaries. Any architectural deviation requires explicit change review.
**Pre-freeze amendment:** Serum execution and readback ownership locked (section 7.2, 28, 28.1, 28.2, 29): Serum MCP manipulates Serum state/presets; the Ableton UI is the delivery boundary that loads the preset into the Ableton-hosted Serum 2.0.21; Direct UI/readback inspects and verifies the actual Serum state; Ableton MCP does not manipulate Serum. The earlier text describing Ableton-hosted plugin-state readback was removed, and the DawDreamer plugin-host experiment is retained only as historical / experimental evidence (not a canonical execution, manipulation, readback, or fallback path).
**Implementation baseline:** commit `2b02fd7` (branch `vlp1-fresh-run-td22-fixes`)  
**Core runtime:** Claude Code  
**Instrument:** Serum 2.0.21  
**DAW:** Ableton Live 12  
**Canonical Serum execution:** serum-mcp  
**Canonical DAW execution:** Ableton MCP where capability exists  
**Freedom-domain execution:** Freedom MCP where applicable  

---

# 1. Purpose

The system reconstructs a music-production process from a tutorial by combining timestamped transcript evidence with complete visual UI evidence, converting that evidence into an ordered production timeline and canonical intent, reasoning through the existing Producer Brain, resolving only verified capabilities, authorizing execution through Admission, executing in the correct backend, verifying the resulting real state, persisting the experience, and replaying it without the original source.

This is **not** a transcript-to-preset shortcut.

The canonical chain is:

```text
Tutorial Source
      ↓
Transcript Evidence
      +
Visual Frame Evidence
      ↓
Claude Code Stage-A Visual Observation
      ↓
Pure Evidence Ingestion
      ↓
UIStateSnapshot
      ↓
Reference Canonicalization
      ↓
Snapshot / Route Diff
      ↓
Production Timeline
      ↓
Transcript + Visual Fusion
      ↓
ProductionEvent
      ↓
UniversalProductionIntent / ProducerRequest
      ↓
Producer Brain
      ↓
Capability Resolution
      ↓
Admission
      ↓
Authorized Domain Execution
  ├── Serum   → Serum MCP → Ableton UI (load preset) → Real Serum → Direct UI
  ├── Ableton → Ableton MCP
  └── Freedom → Freedom MCP
      ↓
Readback + Readback Route Provenance
      ↓
Render / Acoustic Measurement
      ↓
VerifiedEpisode
      ↓
ProductionMemory
      ↓
Source-Free Replay
```

---

# 2. Fundamental Architectural Separation

The system has five independent layers:

```text
REFERENCE
PURE LOGIC
EPISODIC / LEARNED EVIDENCE
CAPABILITY
AUTHORITY
```

These layers must not silently collapse into one another.

The core invariant is:

> **Reference facts do not become logic. Logic does not become evidence. Evidence does not become authority. Capability does not become Admission.**

Additional frozen invariants:

- Producer Brain is the single reasoning/decision layer.
- There is no second planner, second brain, hidden gate, or second authoritative store.
- Memory is advisory only.
- Visual observation never directly mutates Serum or Ableton.
- Registry/reference existence never implies executability.
- Planning, execution, readback, and verification are separate states.

A transition between layers must be explicit and testable.

---

# 3. Layer 1 — Reference Knowledge

## 3.1 Purpose

Reference knowledge answers:

> What exists in Serum 2.0.21, what is it called, what semantic identity does it have, what options/structure are actually established, and what evidence supports that reference fact?

Reference knowledge does **not** decide:

- what the tutorial should change,
- what an artist should sound like,
- what a genre should use,
- which action should execute,
- whether the current tutorial state matches the reference.

## 3.2 Authoritative 908-Record Serum Audit

The permanent Serum reference foundation is the UI-verified **908-record Serum 2.0.21 semantic inventory**.

The frozen audit is the highest-trust reference source for semantic facts actually established by that audit.

Where present, records include:

- semantic ID
- section
- module
- submodule
- label
- control type
- value range
- options
- default
- conditional visibility
- cross references
- structural action
- sources/evidence
- verification status
- notes

The audit is versioned and hash-verified.

Frozen audit facts currently relied upon by VLP-1:

```text
records: 908
unique semantic_id: 908
status: 879 VERIFIED / 23 PROVEN_NOT_USER_CONTROL / 6 UNVERIFIED_CANDIDATE
```

The audit includes semantic identity, control type, options/ranges/defaults where established, conditional visibility, cross-references, structural actions, source evidence, status, and notes. It remains the canonical reference snapshot; derived execution matrices are not promoted into the reference layer merely because they are useful to runtime code.

Known reference limits remain explicit: the audit does not itself provide a complete oscillator-mode selector model, wavetable/sample identity model, graphical/region model, or per-mode structural split. Those may be supplied by separately proven reference data or episode observation, but may not be invented.

## 3.3 Integrated Atlas

The project maintains one canonical integrated reference registry.

The integrated registry may contain:

- audit-backed entries,
- schema-backed entries,
- explicitly sourced UI supplements,
- compatible derived bridges.

However:

> **The raw 908-record audit retains the highest evidentiary status.**

Derived/implementation-authored mappings must remain distinguishable from audit-verified facts.

## 3.4 Reference provenance

Reference provenance must be available wherever the reference layer influences interpretation.

Minimum provenance:

```text
SERUM_VERSION
CONTROL_ATLAS_VERSION
UI_ATLAS_VERSION
SOURCE_AUDIT_VERSION
SOURCE_AUDIT_HASH
```

Where useful, also preserve:

```text
SOURCE_AUDIT_FILENAME
SOURCE_AUDIT_RECORD_COUNT
```

## 3.5 Alias data versus alias logic

Aliases are **reference data**.

The resolution algorithm is **pure logic**.

A new alias requires reference provenance.

The resolver itself is generic and may use a deterministic sequence such as:

```text
Exact canonical ID
    ↓
Exact normalized label
    ↓
Atlas-backed alias match
    ↓
Generic normalized/fuzzy matching, where supported
    ↓
EXACT / ALIAS / AMBIGUOUS / UNRESOLVED
```

A new alias is a **data change**.

A new matching/scoring strategy is a **logic change**.

Neither may become a tutorial-specific rule.

## 3.6 Reference ambiguity

If a surface form maps to multiple legitimate canonical candidates and current evidence does not disambiguate them:

```text
AMBIGUOUS
```

must be preserved.

The system must not silently choose one.

Example:

```text
"cutoff"
    ↓
filter1.cutoff
filter2.cutoff
```

If no additional context exists, the result remains ambiguous.

---

# 4. Layer 2 — Pure Logic

Pure logic is domain-aware implementation that is not tied to a specific tutorial, artist, genre, or fixed tutorial outcome.

Examples:

- timestamp alignment
- interval reasoning
- observation-status handling
- snapshot comparison
- route comparison
- canonical resolution algorithms
- ambiguity detection
- evidence normalization
- timeline construction
- deterministic serialization
- replay mechanics
- generic candidate construction

Pure logic must:

- be deterministic where expected,
- be independently tested,
- avoid tutorial-specific mappings,
- preserve provenance,
- return explicit uncertainty where necessary.

> **Generic does not mean automatically correct.**

Generic logic requires its own tests.

---

# 5. Layer 3 — Episodic and Learned Evidence

## 5.1 Episode evidence

Episode evidence records what a particular tutorial actually showed.

Examples:

```text
ENV1.Release: 15ms → 120ms
OSC B.Unison: 1 → 3
Noise: enabled
Filter 1: MG Low 18
```

These are not permanent Serum reference facts.

They are episode facts tied to source/frame/timestamp provenance.

## 5.2 ProductionMemory

ProductionMemory stores verified experiences for future reasoning.

Memory is advisory.

Memory may influence:

- retrieval
- contextual reasoning
- candidate generation
- ranking
- skills
- reflection

Memory cannot grant execution authority.

## 5.3 Learned behavior

Future learned skills/ranking can produce behavior that looks like a mapping.

It is not hardcoding when it is:

- derived from persisted episodes,
- provenance-backed,
- associated with outcomes/statistics,
- advisory,
- subject to later degradation/removal,
- still forced through the same Capability Resolution and Admission path.

---

# 6. Layer 4 — Capability

Capability answers:

> Can this canonical intent actually be executed through a qualified, verified binding?

A control may be:

- reference-known,
- Brain-unknown,
- Brain-known but unqualified,
- qualified but not admitted.

These are intentionally independent.

Capability may be represented through contracts such as:

```text
CAUSAL_VERIFIED
STRUCTURAL_ONLY
BLOCKED_CONTRADICTED
NEGATIVE_EVIDENCE
UNSUPPORTED
```

A reference entry does not imply executable capability.

A Brain concept does not imply executable capability.

---

## 6.1 Coverage Independence

Reference coverage, Brain vocabulary, and capability coverage are three independent axes. Authority is a fourth, downstream axis. They may differ in any direction.

```text
Control known to Atlas, unknown to Brain
  → REFUSED_NO_BRAIN_CONCEPT

Control known to Brain, no qualified contract/binding
  → REFUSED_NO_CAPABILITY

Capability qualified, Admission denies
  → REFUSED_ADMISSION
```

Consequences:

- Expanding the Atlas never expands execution reach.
- Adding a Brain concept without a verified capability produces refusal, not execution.
- A qualified capability with no Brain concept is unreachable through the Brain, by design.
- Admission remains independent even when capability coverage exists.

The Atlas is not the Brain vocabulary. The Brain vocabulary is not the capability registry. A capability registry is not the Admission authority.


# 7. Layer 5 — Authority

Execution authority is held by:

```text
Capability Resolution
        ↓
Admission
```

Required state distinctions:

```text
CONTRACT_EXISTS
BOUND
RESOLVED
ADMITTED
EXECUTED
READ_BACK
VERIFIED
```

These states must not collapse into one boolean.

---

## 7.1 Refusal Taxonomy

Refusal is a first-class, expected, auditable outcome. The four execution-boundary refusal points are distinct and may not be collapsed.

| Refusal | Emitted by | Condition | Meaning |
|---|---|---|---|
| `REFUSED_UNRESOLVED_REFERENCE` | Reference resolution | No canonical identity in the Atlas | We do not know what this control is. |
| `REFUSED_NO_BRAIN_CONCEPT` | Producer Brain | Canonical identity exists but no supported Brain concept exists | We know what it is; we do not yet reason about it. |
| `REFUSED_NO_CAPABILITY` | Capability Resolution | Brain concept exists but no qualified contract/binding exists | We reason about it; we cannot safely execute it. |
| `REFUSED_ADMISSION` | Admission | Capability exists but authorization is denied | It is executable in principle but not authorized here. |

Reference ambiguity is handled before Brain lookup and is represented as a separate resolution state: `REFUSED_AMBIGUOUS_REFERENCE`.

Frozen refusal rules:

- Every refusal carries a machine-readable reason code and emitting layer.
- The refusal is persisted in the decision trace and, when applicable, in `VerifiedEpisode`.
- A refusal terminates the request. No layer may substitute a different target, concept, capability, or backend.
- A refusal is not permission to fall through to a broader heuristic.


## 7.2 Execution Surfaces Are Not Authority

Serum MCP, Ableton MCP, Freedom MCP, the Ableton UI (preset delivery), and Direct UI are **execution and observation surfaces**. None of them is an authority layer.

Every action on any surface, including a post-load correction made through Direct UI, must first pass:

```text
Producer Brain
  ↓
Capability Resolution
  ↓
Admission
  ↓
authorized capability on that surface
```

Access to a surface is not a capability. A surface that can perform an action does not thereby have permission to perform it.


# 8. Coverage and Authority Independence Matrix

The architecture treats four dimensions separately:

```text
REFERENCE COVERAGE
BRAIN VOCABULARY
CAPABILITY COVERAGE
EXECUTION AUTHORITY
```

A request may move forward only when each required layer is satisfied independently.

| State | Result |
|---|---|
| Atlas knows control; Brain does not | `REFUSED_NO_BRAIN_CONCEPT` |
| Brain knows concept; no qualified capability | `REFUSED_NO_CAPABILITY` |
| Capability is qualified; Admission denies | `REFUSED_ADMISSION` |
| All required layers satisfied | Execution may proceed |

Therefore:

```text
Atlas entry
    ≠ Brain concept

Brain concept
    ≠ qualified capability

Qualified capability
    ≠ automatic Admission
```

Adding coverage to one layer never implicitly extends another. This independence is an architectural invariant and is checked during development review.

# 9. No-Hardcoding Invariant

The architecture prohibits developer-authored tutorial-specific mappings.

Forbidden examples:

```text
artist → Serum parameters
genre → Serum parameters
tutorial title → preset settings
timestamp → fixed mutation
phrase → arbitrary MCP operation
video → hardcoded wavetable
specific tutorial → fixed control sequence
```

Also forbidden as execution rules:

```text
"longer" → release
"shorter" → release
"more" → arbitrary control
"less" → arbitrary control
```

unless a generic language interpretation operates only after canonical target resolution and cannot alter the established target.

## 9.1 Generic derivation rule

Before adding new behavior ask:

> **Can this be derived from the Reference Atlas + current evidence + existing generic logic + verified capability contracts?**

If yes:
→ implement generically.

If no:
the missing piece must be one of:

1. provenance-backed reference data,
2. episodic/learned evidence,
3. newly qualified capability,
4. explicit refusal/unsupported result.

It must not become a tutorial-specific developer rule.

---

# 10. Stage-A Runtime Boundary

Claude Code is the canonical Stage-A visual reasoning runtime. Stage-A observation is an **external model-produced input** to the deterministic pipeline.

Canonical flow:

```text
Claude Code
    ↓
direct frame inspection
    ↓
structured Stage-A observation JSON
    ↓
pure ingest_stage_a_observation()
    ↓
UIStateSnapshot
```

The deterministic project pipeline does **not**:

- run Stage-A itself,
- call Claude to obtain observations,
- require an Anthropic SDK,
- require `ANTHROPIC_API_KEY`,
- introduce another model client or model authority.

Stage-A JSON is a first-class artifact and must carry its own provenance, at minimum:

```text
observer
observation_mode
model_api_used
source/frame manifest
observation schema/version
```

This separation means that observation quality may change independently of deterministic pipeline code. Source-free replay consumes persisted Stage-A JSON and never re-invokes the observer.

# 11. Full Visual Census

Claude Code must inspect the visible UI independently of transcript scope.

The transcript is an evidence source and temporal/context hint.

It is not the visual enumeration boundary.

For each relevant frame, Stage-A should attempt to identify:

- visible surfaces/panels
- active mode
- visible controls
- selectors
- textual identities
- graphs
- curves
- regions
- routes
- topology
- enable/bypass state
- module ordering
- visually legible values

Unmentioned visible state must still be captured.

---

# 12. Observation Status Semantics

Observation status is operational evidence. Statuses are not interchangeable and must never be collapsed.

## OBSERVED

The surface is visible, legible, and sufficiently resolved for the recorded observation. Current-frame state may participate in snapshot comparison and diffing.

## NOT_OBSERVED

The surface was not checked or not established in this frame. No current-frame conclusion is drawn.

## OUT_OF_VIEW

The surface would not be visible in the current viewport/page state. This is positive evidence about visibility, not evidence that the surface disappeared or changed.

## OCCLUDED

The surface is within the relevant viewport but blocked by another UI element, overlay, tooltip, presenter, or obstruction. The occlusion may itself be recorded as an episode fact.

## AMBIGUOUS

The surface is visible/legible enough to establish that something is present, but identity, value, or state cannot be uniquely decided.

Frozen downstream rule:

```text
NOT_OBSERVED / OUT_OF_VIEW / OCCLUDED / AMBIGUOUS
    ↓
No current state change is inferred
```

A prior observed value may be retained as **historical context only**. It is never treated as current-frame evidence merely because a surface is not currently observable.

Never:

```text
not visible → removed
unreadable → guessed number
ambiguous → silent selection
previous value → current value without observation
```

# 13. UIStateSnapshot

Each relevant frame can produce a `UIStateSnapshot`.

It retains:

- frame identity/provenance
- timestamp
- controls
- routes
- raw labels
- canonical identities
- resolution status
- observation status
- structured detail
- placement/provenance where available
- surface/mode information

Structured `detail` may represent non-scalar state such as:

- graph state
- curve points
- region bounds
- route rows
- ordering
- other verified structured UI state

---

# 14. Serum UI State Model

The Serum UI contains more state than scalar parameters.

Reference/observation elements may be:

```text
CONTROL
SELECTOR
TEXT_IDENTITY
GRAPH
CURVE
REGION
ROUTE
TOPOLOGY
ENABLE_STATE
```

This allows the system to model:

- knobs/sliders
- dropdown/menu selections
- wavetable/sample names
- graph/curve state
- sample regions
- modulation routes
- mixer/FX topology
- enabled/bypassed state
- module order

---

# 15. Oscillator Model

Serum 2 supports multiple oscillator modes.

At minimum the architecture recognizes:

```text
WAVETABLE
SAMPLE
MULTISAMPLE
GRANULAR
SPECTRAL
```

Mode is state.

Mode-specific elements must not be fabricated across incompatible modes.

Conceptually:

```text
OSC A
 ├── mode
 ├── common state
 └── mode-specific state
```

## 15.1 Wavetable

Where established by trusted reference evidence or actual visual evidence:

- wavetable identity/name
- frame/position
- interpolation
- tuning mode
- unison configuration
- warp mode 1
- warp amount 1
- warp mode 2
- warp amount 2
- phase
- phase randomization
- routing
- graphical/table state

## 15.2 Sample

Where established:

- sample identity
- start/end
- loop start/end
- crossfade
- slicing
- playback mode
- warp
- graphical region

## 15.3 Other modes

Multisample, Granular and Spectral state must only use semantics established by trusted evidence or direct observation.

Unknown semantics remain unknown.

---

# 16. Atlas Normalization

Raw observations are normalized against the reference layer:

```text
Raw Stage-A Observation
        ↓
Atlas Canonical Resolution
        ↓
Canonical Identity
```

Resolution results:

```text
EXACT
ALIAS
AMBIGUOUS
UNRESOLVED
```

The original observed label is preserved.

The normalized observation preserves:

- raw label
- canonical ID if resolved
- resolution status
- resolution provenance
- observed value
- observation status

The Atlas cannot manufacture a current-frame value.

---

# 17. Canonical Resolution Pipeline

Resolution is a fixed ordered pipeline. The order is architectural and may not be reordered by caller, feature, or tutorial.

```text
surface form / explicit target
        ↓
Atlas canonical resolution
        ├── UNRESOLVED → REFUSED_UNRESOLVED_REFERENCE
        ├── AMBIGUOUS  → REFUSED_AMBIGUOUS_REFERENCE
        └── EXACT / ALIAS → canonical ID
                 ↓
          Brain concept lookup
                 ├── missing → REFUSED_NO_BRAIN_CONCEPT
                 └── present → canonical Brain concept
                              ↓
                 generic language heuristics
                 (canonical concept only)
                              ↓
                    Capability Resolution
                     ├── no qualified capability → REFUSED_NO_CAPABILITY
                     └── qualified → candidate
                                    ↓
                               Admission
                                ├── denied → REFUSED_ADMISSION
                                └── granted → execution
```

Invariant: generic heuristics **may not see the raw surface form when resolving target identity**. They may refine attributes such as direction only after a canonical concept is established.

No step may substitute a different canonical target merely because a heuristic matches it better.

# 18. Explicit Target Safety

An explicit semantic target always has priority over generic language heuristics.

Example:

```text
semantic_target = Env1.Decay
```

may not become:

```text
Env1.Release
```

just because the raw phrase contains `shorter`, `longer`, `more`, or `less`.

The safe behavior is:

```text
explicit target
   ↓
Atlas resolution
   ↓
canonical ID
   ↓
Brain concept
   ↓
heuristic refinement of direction/operation
```

If the canonical target has no Brain concept, the result is `REFUSED_NO_BRAIN_CONCEPT`. It must not fall through to another concept.

This rule closes the demonstrated `Env1.Decay` → `Env1.Release` failure mode without adding a tutorial-specific keyword mapping.

# 19. Refusal Taxonomy and Persistence

The architecture exposes refusal at the exact layer where the request becomes unsatisfied.

```text
Reference Resolution
  ├── REFUSED_UNRESOLVED_REFERENCE
  └── REFUSED_AMBIGUOUS_REFERENCE

Producer Brain
  └── REFUSED_NO_BRAIN_CONCEPT

Capability Resolution
  └── REFUSED_NO_CAPABILITY

Admission
  └── REFUSED_ADMISSION
```

Every refusal record must preserve:

- reason code
- emitting layer
- canonical target, when known
- relevant request/intent ID
- reference provenance, when resolution occurred
- timestamp/episode provenance

Refusal terminates the request. The system may expose the refusal as a useful, auditable result, but it may not silently substitute another target or execution path.

# 20. Snapshot Diff

Snapshot comparison uses:

```text
changed_controls
unchanged_controls
newly_observed_controls
not_observed_controls
removed_controls
```

Semantics:

### changed_controls

Both comparable observations exist and the observed state changed.

### unchanged_controls

Both comparable observations exist and remain equivalent.

### newly_observed_controls

The element became observable.

This does not mean it was created.

### not_observed_controls

Evidence is insufficient to compare state.

### removed_controls

Requires positive evidence that the element actually disappeared.

The same principle applies to routes and topology.

A route becoming visible after Matrix was out of view is not automatically a newly created route.

---

# 21. Timeline

The production timeline is deterministic glue over already existing evidence/fusion mechanisms.

```text
Ordered UIStateSnapshots
        +
Ordered TranscriptSegments
        ↓
Consecutive/comparable intervals
        ↓
diff_snapshots()
        ↓
Transcript alignment
        ↓
fuse_transcript_and_visual()
        ↓
Ordered ProductionEvent[]
```

The timeline must not create:

- a second planner,
- a second evidence store,
- a second fusion engine.

If a control disappears from view and later reappears, the timeline may compare against the last valid observed state where evidence permits.

No evidence-backed change → no spurious event.

---

# 22. Evidence Fusion

Fusion classifications:

```text
AGREEMENT
VISUAL_ONLY
TRANSCRIPT_ONLY
CONFLICT
UNKNOWN
```

## Direction evaluation

Direction is evaluated **per changed control**.

For each control whose state changed between comparable snapshots:

1. Extract the direction from the visual delta, if available.
2. Extract the stated direction from the aligned transcript, if available.
3. Classify the control:
   - both present and disagree → `CONFLICT`
   - either absent or indeterminate → `UNKNOWN`
   - both present and agree → `AGREEMENT`

Event-level classification is then derived from the per-control classifications:

- any per-control `CONFLICT` → event `CONFLICT`
- no `CONFLICT`, at least one `AGREEMENT` → event `AGREEMENT`
- visual deltas without transcript coverage → `VISUAL_ONLY`
- transcript statements without visual deltas → `TRANSCRIPT_ONLY`
- otherwise → `UNKNOWN`

`CONFLICT` requires positive evidence of contradiction for the specific changed control. A generic directional word elsewhere in the transcript is not a contradiction.

If direction cannot be evaluated reliably for the specific control, use `UNKNOWN`, never `CONFLICT`.

# 23. ProductionEvent

ProductionEvents represent evidence-backed production statements or changes.

They preserve provenance to:

- source frames
- timestamps
- observation
- transcript evidence
- fusion classification

Multiple independent changes may come from one interval.

They must remain separate when semantically independent.

---

# 24. UniversalProductionIntent / ProducerRequest

ProductionEvents become canonical intents/requests.

Examples:

```text
CHANGE_ENVELOPE
CHANGE_FILTER
CHANGE_OSCILLATOR
CHANGE_WAVETABLE
ADD_MODULATION_ROUTE
CHANGE_EFFECT
CHANGE_ROUTING
```

Intent remains separate from execution authority.

---

# 25. Producer Brain

Producer Brain is the single reasoning/decision layer.

It may use:

- production context
- world model
- memory/skills
- value model
- decision model
- candidate requests

It does not directly execute MCP operations.

Brain concept mapping must be canonical-ID based where possible.

---

# 26. Capability Resolution

Capability Resolution determines which verified capability can satisfy a canonical intent.

It must check:

- contract existence
- qualification
- binding
- prerequisites
- scope
- limitations
- provenance

If no qualified capability exists:

```text
REFUSED_NO_CAPABILITY
```

Capability Resolution cannot manufacture a binding.

---

# 27. Admission

Admission is the execution authorization boundary.

It verifies the conditions required for execution.

Admission denial produces:

```text
REFUSED_ADMISSION
```

No reference entry, memory item, Brain preference, or learned skill can bypass Admission.

---

# 28. Serum Execution

The Serum execution boundary is explicit and permanent. It is not defined by whichever host or tool happened to be used during an experiment.

Serum 2.0.21 is hosted inside Ableton Live. That hosting is why the Ableton UI appears in the Serum delivery path, and it is the only reason: it does not make Ableton MCP a Serum manipulation mechanism.

```text
Producer Brain
  ↓
Capability Resolution
  ↓
Admission
  ↓
Serum MCP
  ↓
Serum state / .SerumPreset (artifact + hash persisted)
  ↓
Ableton UI: load the preset into the Ableton-hosted Serum 2.0.21
  ↓
Real Serum 2.0.21 (actual plugin state)
  ↓
Direct UI: inspection / interaction
  ↓
Direct UI readback
  ↓
Comparison (intended vs observed)
  ↓
READ_BACK
  ↓
VERIFIED
```

Roles are distinct and non-interchangeable:

```text
Serum MCP   = the ONLY authorized MCP for Serum manipulation
              (state manipulation / preset construction)
Ableton UI  = the real-plugin DELIVERY boundary: puts the generated
              preset into the Ableton-hosted Serum 2.0.21 instance
Direct UI   = the real-plugin INSPECTION / verification boundary:
              interaction with and readback of the actual Serum instance
Ableton MCP = Ableton-domain operations only; NOT a Serum manipulation
              or Serum verification mechanism
```

The permanent statement of this boundary is:

**Serum MCP is the authoritative Serum manipulation mechanism; the Ableton UI is the real-plugin delivery boundary used to load the generated Serum preset into Serum 2.0.21, and Direct UI/readback is used to inspect and verify the resulting actual Serum state. Ableton MCP remains responsible only for Ableton-domain operations and does not replace Serum MCP for Serum manipulation.**

The Direct UI observation is evidence about the **real plugin**, not merely a representation generated by the MCP.

Important boundaries:

```text
preset generated ≠ preset accepted
preset accepted ≠ readback verified
readback ≠ full verification unless watched state is compared
```

Delivery through the Ableton UI and inspection through Direct UI are **not** a generic escape hatch. After Serum MCP produces the intended state and it is loaded into real Serum, the system verifies through Direct UI. If something is wrong, the system may not start operating arbitrary Serum controls. Any post-load mutation must itself be:

```text
Brain
  ↓
Resolution
  ↓
Capability Resolution
  ↓
Admission
  ↓
authorized Serum capability
  ↓
Direct UI execution
  ↓
Direct UI readback
```

A visual click that happens to work is not itself a capability. UI access may not be used to bypass a missing contract, missing binding, or Admission denial. No Stage-A visual observation directly mutates Serum.

Loading a preset through the Ableton UI is a UI action and must be recorded as such (delivery route `ABLETON_UI_LOAD`); it must never be labelled as Ableton MCP execution (section 30).

## 28.1 Domain Ownership

| Operation | Authority / surface |
|---|---|
| Decide what Serum should do | Producer Brain |
| Authorize it | Capability Resolution, then Admission |
| Create / manipulate Serum preset or state | **Serum MCP** |
| Put the preset into the real, Ableton-hosted Serum instance | **Ableton UI** (delivery boundary) |
| Inspect actual Serum controls / state | **Direct UI** on the real Serum instance |
| Ableton session / track / clip / device operations | Ableton MCP |
| Freedom-domain operations | Freedom MCP |
| Verification | Readback + comparison |

| Domain | Manipulation | Verification / observation |
|---|---|---|
| **Serum** | **Serum MCP** (delivered via the Ableton UI) | **Direct UI** |
| Ableton | Ableton MCP | Ableton/host UI as explicitly authorized |
| Freedom | Freedom MCP | Freedom-domain observation |

No generic MCP may substitute for Serum MCP, and no generic UI automation may bypass the capability/admission chain.

## 28.2 Historical Experimental Evidence (Non-Canonical)

A headless experiment loaded the Serum 2.0.21 VST3 through DawDreamer and read host parameters. It is retained only as:

```text
Experimental validation evidence:
PLUGIN_HOST_READBACK via DawDreamer + Serum 2.0.21 VST3
```

It is classified as:

```text
historical / experimental evidence
NOT canonical execution
NOT canonical manipulation
NOT canonical readback authority
NOT an alternative fallback
```

It may corroborate an episode. It may not stand in for Serum MCP + Direct UI, and no implementation may adopt it as a shortcut.

# 29. Readback Provenance and Route

The authoritative Serum readback route is **Direct UI** of the real Serum 2.0.21 instance.

The readback route is part of episode provenance and must be recorded explicitly, for example:

```json
{
  "readback": {
    "domain": "serum",
    "route": "DIRECT_UI",
    "plugin": "Serum",
    "version": "2.0.21",
    "delivery_route": "ABLETON_UI_LOAD"
  }
}
```

The evidence model distinguishes at least:

```text
DIRECT_UI
PLUGIN_HOST_READBACK
STANDALONE_PLUGIN_INSPECTION
SCREEN_INSPECTION
```

These routes carry different evidentiary weight and are **not interchangeable**. In particular:

```text
PLUGIN_HOST_READBACK ≠ DIRECT_UI
```

unless the episode contains separate evidence establishing both. For VLP-1 the authoritative Serum route is **Serum MCP + Direct UI**; other routes may corroborate but cannot by themselves establish `VERIFIED` for Serum state.

Every readback record must include:

- domain
- delivery route by which the state reached the real plugin (e.g. `ABLETON_UI_LOAD`)
- route identifier
- host/plugin/backend identity and version
- route capability/version when available
- watched semantic controls/state
- expected state
- observed state
- comparison result
- timestamp/run provenance
- artifact or inspection provenance

A phrase such as "host route" without a concrete route record is insufficient for verification claims.

Ableton remains a separate domain: Ableton MCP for Ableton/session/track/device operations. It does not become the authority for Serum state manipulation or Serum verification. The Ableton UI's role for Serum is limited to delivering the generated preset into the hosted Serum instance (section 28).

---

# 30. Ableton Execution

Ableton MCP is authoritative for supported DAW/session operations:

- tracks
- clips
- MIDI
- arrangement
- automation
- session state
- render/export where capability exists

If a UI fallback is temporarily required because an MCP capability does not exist, the episode must explicitly identify the fallback and must not label it as MCP execution. Loading a Serum-MCP-generated preset into the hosted Serum through the Ableton UI is such a UI action: it is recorded as `ABLETON_UI_LOAD`, and it does not make Ableton MCP a Serum manipulation mechanism.

---

# 31. Freedom MCP

Freedom MCP is only for Freedom-domain capabilities.

It is not a generic execution fallback.

Freedom operations still follow:

```text
Intent
→ Brain
→ Capability Resolution
→ Admission
→ Freedom MCP
```

---

# 32. Audio Measurement

G8 acoustic measurement is corroborating evidence.

Where used, persist:

- RMS
- peak
- spectral centroid
- duration
- SHA-256
- measurement definition
- kernel version
- channel policy
- status

Audio does not replace canonical application-state verification.

---

# 33. VerifiedEpisode

`VerifiedEpisode` is the persistent audit object for one production episode.

It stores, as applicable:

- source provenance
- transcript provenance
- frame manifest/provenance
- Stage-A JSON and observer provenance
- observation-status data
- raw and canonical observations
- inferred-vs-observed separation
- UIStateSnapshots
- snapshot/route diffs
- timeline
- ProductionEvents
- UniversalProductionIntents / ProducerRequests
- Brain decision trace and version/provenance
- capability resolution trace
- capability/contract/binding versions used
- admission decision and policy/version provenance
- execution backend and version/provenance
- execution artifacts and hashes
- readback route and state
- preset hash, where applicable
- render hash, where applicable
- audio measurements, where applicable
- final verification classification
- refusal states, when the episode contains a refused request
- reference provenance

## 33.1 Reference provenance

Persist reference provenance separately from tutorial/source attribution, for example:

```text
provenance["reference_provenance"]
```

Minimum fields:

```text
SERUM_VERSION
CONTROL_ATLAS_VERSION
UI_ATLAS_VERSION
SOURCE_AUDIT_VERSION
SOURCE_AUDIT_HASH
```

Where applicable also persist:

```text
SOURCE_AUDIT_FILENAME
SOURCE_AUDIT_RECORD_COUNT
```

Reference provenance is pinned to the episode. Current Atlas versions may not silently replace the provenance of an older episode.

## 33.2 Execution/replay provenance

For any episode that may claim source-free re-execution, persist enough version/binding information to identify the original decision and execution environment, including at minimum:

```text
brain_logic_version
reference_provenance
capability_contract_versions
capability_binding_versions
admission_policy_version
execution_backend_versions
readback_route_versions
```

If any required pin is missing, the episode may still be loadable for memory/analytics, but the system must downgrade or refuse claims that depend on that missing provenance.

## 33.3 Legacy episodes

An episode without reference provenance is marked:

```text
LEGACY_NO_PROVENANCE
```

Legacy behavior:

- loadable for inspection, memory and analytics: yes
- eligible for source-free replay with full verification: no
- silently reinterpreted using the current Atlas: no

A legacy episode may become replayable only through explicit re-processing against a pinned Atlas version, with the resulting reference and replay provenance recorded.

# 34. Source-Free Replay

Replay is source-free only when the original tutorial source is not reacquired and the replay consumes persisted episode artifacts alone. At minimum, the replay must proceed with the original transcript, frames, source/network access, and observer unavailable.

Replay mode is explicit:

```text
REPLAY_EXECUTE
REPLAY_SIMULATE
```

Both modes require `reference_provenance`. `REPLAY_EXECUTE` additionally requires the version/binding provenance necessary to reproduce the execution environment.

## 34.1 REPLAY_EXECUTE

Re-execution reconstructs the recorded decision chain and executes it using episode-pinned versions rather than whatever happens to be current.

```text
Persisted episode
  ↓
source-free eligibility check
  ↓
reference provenance pin
  ↓
brain logic/version pin
  ↓
capability contract + binding version pin
  ↓
admission policy/version pin
  ↓
replay decision/resolution
  ↓
authorized backend
  ↓
readback
  ↓
comparison against recorded result
```

Replay must not silently pick up:

- a newer Atlas
- a newer capability contract
- a different execution binding
- a changed Admission policy
- a different Brain implementation
- the original tutorial source/network

If a required historical pin is unavailable, the system must report replay-verification-unavailable rather than pretending the current environment is equivalent.

If replay produces a different resolution, capability, admission, execution, readback, hash, or measurement outcome, the divergence is an audit finding and must be surfaced. It may not be silently normalized away.

## 34.2 REPLAY_SIMULATE

Simulation reconstructs the decision chain without touching an execution backend. It uses the recorded episode admission outcome and does **not** claim to newly authorize execution.

Simulation may report:

```text
DERIVED
MATCHED
DIVERGED
UNAVAILABLE
```

Simulation may never claim `EXECUTED`, `READ_BACK`, or `VERIFIED` for the new simulation run.

# 35. Anti-Hallucination Invariants

Never infer:

```text
not visible → removed
unreadable → exact number
transcript says → executed
preset generated → accepted
plugin-host readback → DIRECT_UI verified
DawDreamer / host-parameter readback → canonical Serum verification
audio similarity → identical state
reference existence → current observation
reference existence → execution authority
```

Every claim must carry evidence appropriate to that claim.

---

# 36. Development Review Rule

Every proposed change must first be classified by architectural layer.

### Reference fact?

Add provenance-backed reference data.

### Generic processing?

Implement pure, tested logic.

### Episode fact?

Persist it as episode evidence.

### Learned behavior?

Store provenance-backed advisory learning.

### Execution capability?

Qualify a capability contract and binding with evidence.

### Execution authority?

Admission owns it.

### Coverage independence check

Every proposed change must answer both:

```text
Which coverage axis does this extend?
  - Reference coverage (Atlas)
  - Brain vocabulary
  - Capability coverage

Which axis does it NOT extend?
```

Examples:

- Adding an Atlas entry does not extend Brain vocabulary.
- Adding a Brain concept does not extend capability coverage.
- Adding a capability does not grant Admission authority.

If a change appears to extend more than one coverage axis at once, stop and split the change until the layer transition is explicit and independently reviewable.

# 37. Change Review: No Hidden Hardcoding

Before accepting a patch, answer:

```text
Does this contain a tutorial-specific mapping?
Does this contain an artist/genre-specific parameter rule?
Does this contain a timestamp-specific execution rule?
Does this bypass Atlas canonicalization?
Does this bypass Capability Resolution?
Does this bypass Admission?
Does this infer a missing value?
Does this silently turn ambiguity into a decision?
Does this use DawDreamer, a plugin host, a generic MCP, or generic UI automation as a Serum execution or readback path?
Does this operate Serum through Direct UI without Brain -> Capability Resolution -> Admission?
```

Any "yes" requires rejection or architectural redesign.

---

# 38. Current Verified Architecture Evidence

The current implementation baseline has demonstrated a substantial end-to-end slice on a fresh Serum 2.0.21 tutorial run:

- fresh tutorial source
- fresh transcript
- fresh visual frames
- Claude Code direct visual inspection with no Anthropic API/SDK path
- 1,594 visual-census entries
- operational observation statuses and corrected observation bugs
- Atlas normalization with unresolved/ambiguous states preserved
- deterministic snapshot diff and timeline recovery
- per-control production-event fusion pipeline (architecture frozen; runtime quality remains a known gap)
- Producer Brain → Capability Resolution → Admission path
- Serum preset generated through Serum MCP and loaded into a real Serum 2.0.21 VST3 by an experimental DawDreamer host (section 28.2; not the canonical route)
- experimental PLUGIN_HOST_READBACK of the loaded plugin's host parameters (section 28.2; corroborating only)
- G8 render/measurement
- VerifiedEpisode persistence with reference provenance
- source-free replay executed through the same experimental headless host route (section 28.2; not the canonical route)
- regression suite reaching 149 passed, 1 skipped after the fresh-run fixes

The demonstrated run did **not** establish:

- complete execution of every tutorial-observed control
- Direct UI readback of the real Serum instance (the canonical Serum readback route)
- full patch reproduction
- perfect transcript/visual fusion

Those are implementation evidence gaps, not reasons to weaken the frozen architecture.

# 39. Current Known Gaps

The architecture is frozen even though implementation coverage is not complete. Known gaps remain:

1. **Direct UI readback (canonical Serum route):** not yet demonstrated. The latest fresh run's verification used the experimental DawDreamer route (section 28.2), which is corroborating evidence only; canonical Serum verification therefore remains open.
2. **Brain reach:** the Brain currently exposes a smaller vocabulary than the Reference Atlas and qualified capability registry.
3. **Capability coverage:** several observed tutorial controls remain intentionally unqualified until evidence supports them.
4. **Brain-side mappings:** some already-qualified contracts still need canonical Brain concept glue; this must not be confused with capability qualification.
5. **Fusion:** the architecture now requires per-control direction evaluation; runtime classification still requires continued validation against ambiguous narration windows.
6. **Mode-specific visual state:** oscillator mode, wavetable/sample identity, graphical/region details and other transient visual state may remain episode observations unless trusted reference evidence establishes them as permanent reference facts.
7. **Structural operations:** Matrix/FX/Mixer routing and some mode-specific operations remain capability-dependent and must not be promoted from structural observation to causal execution without evidence.
8. **Historical provenance:** older episodes may lack the version pins required for full source-free re-execution and must surface that limitation explicitly.

No gap authorizes a hardcoded substitute, GUI bypass, silent inference, DawDreamer/host-route shortcut, or authority collapse.

# 40. Post-VLP-1 Learning Roadmap

Only after the core VLP-1 loop is stable:

## P3 — Skill Library

Extract reusable production skills from verified episodes.

## P4 — Candidate Generation and Learned Ranking

Generate multiple candidates and rank them using learned evidence.

## P5 — Reflection Learner

Learn from success/failure/reflection.

## P6 — Audio/Text Grounding

Strengthen multimodal representations.

## P7 — Contextual Policy Learning

Condition decisions on artist/genre/style/role/technique/objective without hardcoded parameter maps.

## P8 — Optional Model Adaptation

Optional adaptation of model behavior.

Learning may improve decision quality.

Learning may never grant execution authority.

---

# 41. VLP-1 Definition of Done

There are two different states and they must not be conflated.

## 41.1 Architecture Freeze

Architecture Freeze establishes the following as mandatory, enforceable contracts for implementation and review:

- independent Reference / Logic / Evidence / Capability / Authority layers
- fixed canonical resolution order
- explicit refusal taxonomy
- coverage independence
- no-hardcoding invariant
- external Stage-A boundary
- operational observation statuses
- per-control fusion conflict rule
- explicit Serum ownership chain
- explicit readback-route provenance
- replay modes and provenance pins
- legacy episode handling
- no second brain/planner/gate/store
- change-review and coverage-independence rules

These boundaries are frozen. Runtime completion is tracked separately in Section 41.2 and Section 43.1.

## 41.2 VLP-1 End-to-End Closure

Full VLP-1 implementation closure requires one real tutorial to demonstrate the complete operational chain:

```text
Fresh source
  ↓
Fresh transcript
  ↓
Fresh frames
  ↓
Claude Code complete visual census
  ↓
Stage-A ingestion
  ↓
Reference canonicalization
  ↓
UIStateSnapshots
  ↓
Diff
  ↓
Timeline
  ↓
Fusion
  ↓
ProductionEvents
  ↓
UniversalProductionIntent
  ↓
Producer Brain
  ↓
Capability Resolution
  ↓
Admission
  ↓
Authorized execution
  ↓
Real readback
  ↓
Render / Measurement
  ↓
VerifiedEpisode
  ↓
ProductionMemory
  ↓
Source-free replay
```

Closure must report the exact level of verification actually demonstrated. It must not upgrade plugin-host readback into DIRECT_UI readback, preset creation into plugin acceptance, or partial execution into full tutorial reproduction.

# 42. Final Authority Chain

The frozen canonical chain is:

```text
SOURCE
  ↓
EVIDENCE
  ↓
OBSERVATION
  ↓
REFERENCE CANONICALIZATION
  ↓
INTERPRETATION / TIMELINE
  ↓
UNIVERSAL PRODUCTION INTENT
  ↓
PRODUCER BRAIN
  ↓
CAPABILITY RESOLUTION
  ↓
ADMISSION
  ↓
AUTHORIZED BACKEND
  ↓
REAL EXECUTION
  ↓
READBACK + ROUTE PROVENANCE
  ↓
RENDER / MEASUREMENT
  ↓
VERIFIED EPISODE
  ↓
PRODUCTION MEMORY
  ↓
SOURCE-FREE REPLAY
```

Canonical refusal branches:

```text
Reference Resolution
 ├── REFUSED_UNRESOLVED_REFERENCE
 └── REFUSED_AMBIGUOUS_REFERENCE

Producer Brain
 └── REFUSED_NO_BRAIN_CONCEPT

Capability Resolution
 └── REFUSED_NO_CAPABILITY

Admission
 └── REFUSED_ADMISSION
```

Frozen authority rules:

- No shortcut path is canonical.
- No layer inherits authority from another layer merely by containing a matching identifier.
- Memory is advisory only.
- A reference match never authorizes execution.
- A capability never silently bypasses Admission.
- A successful execution never implies readback.
- A readback never implies full verification unless the intended state is actually compared through the recorded route.
- Source-free replay never reacquires the original tutorial.

# 43. Architecture Freeze Checklist

Before extending Brain execution vocabulary, verify:

- [ ] 908 UI-verified audit remains hash-stable.
- [ ] Integrated Atlas preserves audit provenance.
- [ ] Reference aliases are data-backed.
- [ ] Alias resolution is generic logic.
- [ ] Explicit target canonicalization precedes heuristics.
- [ ] Four refusal boundaries are machine-visible.
- [ ] Observation statuses have operational meanings.
- [ ] Timeline compares only evidence-comparable states.
- [ ] Fusion conflict requires positive per-control contradiction.
- [ ] Legacy episode behavior is explicit.
- [ ] Replay mode is explicit.
- [ ] Replay preserves capability provenance.
- [ ] Serum readback route is explicit.
- [ ] No tutorial-specific hardcoded mappings exist.
- [ ] Coverage independence is preserved.
- [ ] Brain can be extended without weakening any authority boundary.

Only after this checklist is satisfied should broader Brain execution mapping proceed.

---

# FROZEN ARCHITECTURE DECLARATION

This document is the canonical VLP-1 architecture baseline for the current Serum 2.0.21 + Ableton Live 12 system.

The freeze is a **boundary freeze**, not a claim that every capability is already implemented. Future work may add provenance-backed reference data, generic logic, episodic evidence, learned advisory behavior, qualified capabilities, and verified backend bindings. Future work may not collapse Reference, Logic, Evidence, Capability, or Authority layers; may not introduce tutorial-specific hardcoding; and may not use GUI access, memory, or registry presence as an authority bypass.

Any proposed architectural deviation must be reviewed against this document before implementation.
