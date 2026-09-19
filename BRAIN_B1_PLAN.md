# Producer Brain Phase B1: Canonical Foundation

**Branch:** `vlp1-producer-brain-b1-canonical`  
**Goal:** Eliminate hand-written target→concept tables; derive concepts from frozen data layers  
**Baseline:** 2c0h3z41K58 coverage (2 REFUSED_NO_BRAIN_CONCEPT events → target: 0)  
**Constraint:** All work remains inside frozen VLP-1 architecture boundaries

---

## What B1 Does

Transform the Producer Brain from:

```text
request
    ↓
target lookup (hand-written table)
    ↓
concept assignment
    ↓
Capability Resolution
```

into:

```text
request
    ↓
canonical target (Atlas resolution)
    ↓
representation (from Atlas, contracts, generic language)
    ↓
operation/value interpretation
    ↓
context extraction
    ↓
candidate intent
    ↓
Capability Resolution
```

**Key principle:** Derive what can be derived from existing data; only require Brain augmentation where no derivation path exists.

---

## B1 Scope (Atomic Tasks)

### B1.1: Canonical Representation (FOUNDATION)
**What:** Build a `ConceptRepresentation` struct that unifies how the Brain represents a production concept.

```python
@dataclass
class ConceptRepresentation:
    canonical_target: str          # e.g., "env1.decay"
    atlas_entry: Optional[AtlasControl]
    capability_contract: Optional[Contract]
    operation_type: str            # "numeric", "enum", "toggle", "range", etc.
    value_domain: Optional[ValueDomain]
    generic_language: List[str]    # ["shorter", "longer", etc.]
    context_required: Optional[ContextSpec]
    provenance: str                # "atlas", "contract", "derived", "generic"
    confidence: float
    derivation_chain: List[str]    # audit trail
```

**Why:** Eliminates the pattern of separate hand-written tables (EXPLICIT_TARGET_TO_CONCEPT, UNCOVERED_CONTROL_NOUNS, etc.). One representation covers all cases.

**Test:** 
- Can represent env1.decay from contract alone
- Can represent env1.attack from contract alone
- Can represent filter1.cutoff from Atlas + generic language
- Provenance is traceable

**Input data sources:**
- Atlas (canonical IDs, aliases)
- ContractRegistry (CAUSAL_VERIFIED contracts)
- SemanticTargetMapping (existing Brain vocabulary)
- Generic language tokens (frozen vocabulary)

---

### B1.2: Derivation Engine (CONCEPT CONSTRUCTION)
**What:** Given a canonical target, construct a `ConceptRepresentation` by querying all available data sources in order.

```python
class ConceptDerivationEngine:
    def derive(self, canonical_target: str) -> ConceptRepresentation:
        """
        1. Check contract registry for qualified capability
        2. Check existing semantic mappings
        3. Check generic language patterns
        4. Return representation with provenance
        
        Never invent a concept. Return "derived" or "missing".
        """
```

**Why:** Centralize concept construction; make it auditable and testable.

**Test:**
- env1.decay → CAUSAL_VERIFIED contract exists; derive from it
- env2.decay → same contract available; derive from it (not a separate concept)
- filter1.cutoff → contract exists; derive from it
- oscA.warp_mode → no contract; check generic language; return "derived" if applicable, else "missing"
- oscA.unison → no contract; generic language doesn't apply; return "missing" with explanation

---

### B1.3: Operation/Value Interpretation (INTENT FORMATION)
**What:** Given a concept and user intent ("shorter", "to 5ms", "increase", etc.), produce a normalized operation spec.

```python
@dataclass
class OperationSpec:
    operation: str                 # "numeric_set", "enum_select", "toggle", "increase", "decrease"
    target_value: Optional[Any]
    direction: Optional[str]       # "increase", "decrease"
    unit: Optional[str]
    certainty: float
```

**Why:** Separate language interpretation from concept. This layer should be reusable across concepts.

**Test:**
- "shorter env1.decay to 200ms" → op=numeric_set, value=200, unit=ms, certainty=0.95
- "increase filter cutoff" → op=increase, direction=increase, value=None, certainty=0.85
- "set filter type to band24" → op=enum_select, value="BP12", unit=None, certainty=0.9
- "make it tighter" + context=filter1 → op=increase, direction=increase (resonance), value=None, certainty=0.7

---

### B1.4: Context Extraction (REQUEST METADATA)
**What:** Extract and normalize request context for later reasoning.

```python
@dataclass
class RequestContext:
    explicit_target: Optional[str]
    semantic_target: Optional[str]
    implicit_scope: Optional[str]   # "the filter", "this oscillator", "global"
    time_context: Optional[str]     # "at the end", "gradually", etc.
    audio_context: Optional[str]    # "dark", "warm", "tight", "wide", etc.
    tutorial_context: Optional[str] # episode ID, frame context, etc.
    confidence: Dict[str, float]
```

**Why:** Context matters for later ranking/policy phases. Capture it now in canonical form.

**Test:**
- "shorter env1.decay" → explicit_target="env1.decay", implicit_scope=None
- "make the filter cutoff higher" → implicit_scope="filter1", explicit_target=None
- "add reverb" + context=global FX → semantic_target="reverb", implicit_scope="global"

---

### B1.5: Candidate Intent Formation (UNIFIED OUTPUT)
**What:** Combine representation + operation + context into a single `UniversalProductionIntent` ready for Capability Resolution.

```python
@dataclass
class UniversalProductionIntent:
    canonical_target: str
    representation: ConceptRepresentation
    operation: OperationSpec
    context: RequestContext
    confidence: float
    derivation_trace: List[str]   # audit trail for every step
    input_request: ProducerRequest  # original request
```

**Why:** Single output format that Capability Resolution and Admission can rely on.

**Test:**
- All B1.1–B1.4 outputs combine without loss
- Derivation trace is complete and auditable
- Two requests with same intent produce identical UniversalProductionIntent (idempotent)

---

### B1.6: Refusal Classification (PRESERVE FROZEN TAXONOMY)
**What:** Ensure all refusal codes from the frozen architecture map correctly to B1 derivation failures.

```python
REFUSAL_CODES_B1:
├── REFUSED_UNRESOLVED_REFERENCE     # Atlas has no entry for this name
├── REFUSED_AMBIGUOUS_REFERENCE      # Atlas has multiple matches
├── REFUSED_NO_BRAIN_CONCEPT         # derivation returns "missing"
└── [REFUSED_NO_CAPABILITY]          # (downstream; Capability Resolution handles this)
```

**Why:** B1 failures should be traceable to exact layer. This maintains the frozen refusal taxonomy.

**Test:**
- "set Env1.Bogus to 5" → REFUSED_UNRESOLVED_REFERENCE (Atlas doesn't know Bogus)
- "shorten cutoff" → REFUSED_AMBIGUOUS_REFERENCE (filter1.cutoff vs filter2.cutoff)
- "set oscA.unison to 3" → REFUSED_NO_BRAIN_CONCEPT (concept derivation fails)
- "set env1.decay to 200ms" → (refusal deferred to Capability Resolution)

---

## B1 Test Suite

### Unit Tests (independent layer tests)

**test_canonical_representation.py**
- Can construct from contract
- Can construct from Atlas + generic language
- Provenance is accurate
- Confidence reflects data quality

**test_derivation_engine.py**
- Derives existing concepts correctly
- Returns "missing" for absent concepts
- No invention
- Auditable trace

**test_operation_spec.py**
- "shorter" → decrease
- "faster" → increase (rate contexts) or same (time contexts, e.g., decay)
- "set to value" → numeric_set
- "toggle" → toggle

**test_context_extraction.py**
- Explicit target extracted
- Implicit scope recognized
- Audio descriptors tagged
- Confidence levels assigned

**test_intent_formation.py**
- All pieces combine correctly
- Two identical requests → identical intent
- Trace is complete

**test_refusal_classification.py**
- Each frozen refusal code mapped to B1 scenarios
- No new refusal codes introduced
- Taxonomy unchanged

### Integration Tests (pipeline tests)

**test_b1_baseline_2c0h3z41K58.py**

Run all 9 events from the fresh coverage analysis through B1:

```python
@parametrize
def test_event_1_oscA_warp_mode():
    """Event 1: oscA.warp_mode OFF→REMAP 2"""
    intent = derive_from_event(events[0])
    
    # B1 should produce a representation
    assert intent.representation is not None
    
    # Concept derivation should fail gracefully
    if intent.representation.provenance == "missing":
        assert intent.refusal["code"] == "REFUSED_NO_BRAIN_CONCEPT"
    else:
        # Success case (if future work adds warp_mode concept)
        assert intent.refusal is None
```

Run this for all 9 events:
- Event 1: oscA.warp_mode → measure current refusal
- Event 2: env2.decay/sustain → measure current refusal
- Event 3: routes → should remain unresolved
- Event 4: lfo1.rate/smooth → measure current refusal
- Event 5: filter1.enabled → measure current refusal
- Event 6: lfo1.smooth → measure current refusal
- Events 7–9: metadata/empty → should remain unresolved

**Baseline table:**

| Event | Control | Current | B1 Target | Derivation Path |
|-------|---------|---------|-----------|-----------------|
| 1 | oscA.warp_mode | REFUSED_NO_BRAIN_CONCEPT | ? | Generic language or missing |
| 2 | env2.decay | REFUSED_NO_CAPABILITY | no change (downstream) | Contract-derived |
| 4 | lfo1.rate | REFUSED_NO_CAPABILITY | no change (downstream) | Contract-derived |
| 5 | filter1.enabled | REFUSED_NO_CAPABILITY | no change (downstream) | Contract-derived |
| 6 | lfo1.smooth | REFUSED_NO_BRAIN_CONCEPT | ? | Generic language or missing |

---

## B1 Success Criteria

### Structural
- ✅ ConceptRepresentation defined and used throughout
- ✅ ConceptDerivationEngine implemented; no hand-written target tables
- ✅ OperationSpec and RequestContext capture all intent metadata
- ✅ UniversalProductionIntent is single output format
- ✅ All refusal codes map to B1 derivation failures; no new codes

### Measurable
- ✅ 2c0h3z41K58 baseline events re-tested
- ✅ REFUSED_NO_BRAIN_CONCEPT count documented (target: unchanged or lower)
- ✅ All derivations are auditable (trace present in every intent)
- ✅ No hard-coded concept tables in source code

### Coverage
- ✅ All existing Brain vocabulary is derivable from B1
- ✅ All frozen refusal codes are correctly triggered
- ✅ Baseline 2c0h3z41K58 events tested end-to-end
- ✅ Regression: existing tests still pass

---

## Implementation Notes

### Files to Create/Modify

**New:**
- `serum2/producer/concept_representation.py` — ConceptRepresentation, ConceptDerivationEngine
- `serum2/producer/operation_spec.py` — OperationSpec, intent formation
- `serum2/producer/request_context.py` — RequestContext extraction
- `serum2/producer/universal_intent.py` — UniversalProductionIntent
- `serum2/producer/test_canonical_foundation.py` — all unit tests
- `serum2/producer/test_b1_integration.py` — 2c0h3z41K58 baseline

**Modify:**
- `serum2/producer/producer_brain.py` — wire B1 components; remove hand-written tables
- `serum2/producer/target_resolution.py` — optionally use ConceptDerivationEngine for concept lookup

### Compatibility
- B1 must not break existing test suite
- B1 output (UniversalProductionIntent) must be compatible with Capability Resolution
- Frozen refusal taxonomy must be preserved exactly

---

## Timeline Estimate

- **B1.1–B1.3 (Representation + Derivation + Operations):** 1–2 sessions (core logic)
- **B1.4–B1.5 (Context + Intent Formation):** 1 session (integration)
- **B1.6 (Refusals):** 0.5 session (validation)
- **Test Suite:** 1 session (unit + integration)
- **Baseline Re-test:** 0.5 session (2c0h3z41K58 against B1)

**Total:** ~5 sessions to B1 completion, then move to B2 (Skill Library).

---

## Next: After B1 Completes

Once B1 passes all tests and baseline is re-run:
- Measure coverage improvement by layer
- Report what is still REFUSED_NO_BRAIN_CONCEPT (gaps for later phases)
- Begin B2: P3 Skill Library
