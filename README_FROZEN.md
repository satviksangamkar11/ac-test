# VLP-1: Audited Multimodal Producer Architecture

**Status:** FROZEN + Brain Development Phase  
**Freeze Date:** 2026-09-19  
**Latest Commit:** BRAIN_B1_PLAN (this branch: `vlp1-producer-brain-b1-canonical`)

---

## What This Repository Does

This is a **research implementation** of a multimodal music production assistant that:

1. **Observes** tutorial videos (transcript + visual frames via Claude Code)
2. **Canonicalizes** observations into UI state snapshots (reference Atlas)
3. **Builds** production timelines with transcript/visual fusion
4. **Reasons** through the Producer Brain with explicit authority boundaries
5. **Executes** admitted operations through domain-specific MCPs (Serum, Ableton, Freedom)
6. **Verifies** real state through dedicated readback routes
7. **Learns** from successful/failed episodes for future reasoning

**Core invariant:** Execution authority is never granted by reasoning; the Admission gate is the only mechanism that authorizes execution.

---

## Architecture Status: FROZEN

The complete architectural layer separation is frozen:

```
Reference (Atlas) → Pure Logic → Evidence → Capability → Producer Brain → Capability Resolution → Admission → Execution
```

**What cannot change:**
- Authority boundaries (Admission is sole execution gate)
- Five independent layers (reference ≠ logic ≠ evidence ≠ capability ≠ authority)
- Domain ownership (Serum MCP, Ableton UI/MCP, Freedom MCP)
- Readback routes (Direct UI for Serum verification)
- Refusal taxonomy (reference/brain/capability/admission layers)
- Memory role (advisory only)

**See:** [FREEZE_VLP1.md](FREEZE_VLP1.md)

---

## Producer Brain: Development Phases (Inside Frozen Boundaries)

The Brain can expand substantially without changing architecture:

```
B1 Canonical Foundation
├── derive concepts from Atlas + contracts + generic language
├── eliminate hand-written target→concept tables
└── target: reduce REFUSED_NO_BRAIN_CONCEPT

B2 P3 Skill Library
├── reusable procedures from verified episodes
└── dependency-aware retrieval

B3 P4 Candidate Generation + Ranking
├── multiple candidate strategies
└── advisory ranking only

B4 P5 Reflection
├── structured learning from episodes
└── extractable lessons

B5 P6 Audio/Text Grounding
├── semantic grounding in rendered audio
└── shared embedding space

B6 P7 Contextual Policy
├── context-aware strategy selection
└── mental simulation

[B7 P8 optional Model Adaptation — after mature corpus]
```

**Current Phase:** B1 (Canonical Foundation)  
**See:** [BRAIN_B1_PLAN.md](BRAIN_B1_PLAN.md)

---

## Branches

| Branch | Purpose | Status |
|--------|---------|--------|
| `main` | Stable releases | Archived reference |
| `vlp1-fresh-run-td22-fixes` | TD22 baseline + 2c0h3z41K58 fresh run analysis | Reference |
| **`vlp1-producer-brain-b1-canonical`** | **B1 development (you are here)** | **Active** |

---

## Key Files

### Frozen Architecture
- **[docs/VLP1_Fully_Revised_Architecture.md](docs/VLP1_Fully_Revised_Architecture.md)** — complete spec (frozen 2026-09-19)
- **[FREEZE_VLP1.md](FREEZE_VLP1.md)** — architecture freeze memo
- **[serum2/audit/](serum2/audit/)** — 908-record Serum 2.0.21 UI census + manifest

### Evidence & Pipeline
- **[serum2/reference/serum_atlas.py](serum2/reference/serum_atlas.py)** — canonical control ontology
- **[serum2/producer/target_resolution.py](serum2/producer/target_resolution.py)** — ordered resolution + refusals
- **[serum2/producer/evidence_fusion.py](serum2/producer/evidence_fusion.py)** — per-control direction fusion (§22)
- **[serum2/producer/timeline.py](serum2/producer/timeline.py)** — production event extraction

### Brain
- **[serum2/producer/producer_brain.py](serum2/producer/producer_brain.py)** — current Brain implementation
- **[BRAIN_B1_PLAN.md](BRAIN_B1_PLAN.md)** — B1 canonical foundation plan (next)

### Data & Results
- **[serum2/data/runs/](serum2/data/runs/)** — execution artifacts (gitignored)
  - `td22OIHpWuI/` — TD22 reference run (frozen)
  - `2c0h3z41K58/` — fresh source run (diagnostics)
- **[serum2/data/experiences/](serum2/data/experiences/)** — VerifiedEpisode objects (gitignored)

---

## Coverage Baseline (2c0h3z41K58)

Fresh-run diagnostic dataset used to validate B1 and future phases:

| Layer | Events | Status |
|-------|--------|--------|
| EXECUTABLE | 0 | ❌ No capabilities admitted from fresh source |
| Capability layer | 3 | REFUSED_NO_CAPABILITY (missing contracts) |
| Brain layer | 2 | REFUSED_NO_BRAIN_CONCEPT (missing concepts) |
| Reference layer | 4 | REFUSED_UNRESOLVED_REFERENCE (no semantic intent) |

**Use this as B1 validation:** Re-run all 9 events through B1; measure improvement in refusal distribution.

**See:** [serum2/data/runs/2c0h3z41K58/COVERAGE_REPORT.md](serum2/data/runs/2c0h3z41K58/COVERAGE_REPORT.md)

---

## Development Workflow

1. **Check frozen boundaries** — does the change improve understanding/retrieval/ranking/learning?
2. **Write tests first** — especially baseline re-tests against 2c0h3z41K58
3. **Measure coverage** — run baseline; report refusal distribution before/after
4. **Commit atomically** — one feature per commit with clear provenance
5. **Do NOT modify architecture** — if it requires new authority/layer, it's out of scope for B1–B6

---

## Running the Pipeline

### Fresh Observation (Stage-A)
```bash
# See serum2/data/runs/2c0h3z41K58/build_stage_a.py for example
# Produces: stage_a_observation.json (Claude Code + direct visual inspection)
```

### Timeline + Fusion + Refusal Analysis
```bash
cd serum2/data/runs/2c0h3z41K58
python run_timeline.py              # → events, fusion statuses
python coverage_analysis.py         # → coverage table + refusals
```

### Brain Execution (Current)
```bash
python -c "
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
b = ProducerBrain()
r = b.execute(ProducerRequest(user_intent='set env1.decay to 100ms'))
print(r.refusal or 'ADMITTED')
"
```

---

## Architecture Principles (Frozen)

**Five layers, never collapsing:**
- Reference facts stay facts; logic stays logic
- Evidence does not become authority; authority is only Admission
- Registry/contract existence ≠ executability
- Capability resolution is data-driven; Admission is the sole gate

**Brain principles:**
- Single reasoning layer (no parallel decision systems)
- Memory is advisory; not authoritative
- Visual observation is evidence; not a direct action trigger
- No hard-coded mappings; all derivable from frozen data

**Serum ownership:**
- Serum MCP manipulates → generates .SerumPreset
- Ableton UI loads preset → real plugin state
- Direct UI verifies → readback of actual state
- Ableton MCP ≠ Serum controller

---

## Testing

**Run full test suite:**
```bash
pytest serum2/ -v
```

**Run only baseline diagnostics:**
```bash
cd serum2/data/runs/2c0h3z41K58
python coverage_analysis.py
```

**Measure Brain coverage after changes:**
```bash
# After modifying serum2/producer/producer_brain.py or related:
pytest serum2/producer/test_ordered_resolution.py -v
pytest serum2/producer/test_evidence_fusion.py -v
```

---

## References

**Frozen Architecture:**
- [VLP1_Fully_Revised_Architecture.md](docs/VLP1_Fully_Revised_Architecture.md) — complete spec

**Research Sources (informed B1–B7 design):**
- Phase P3–P8: cognitive stack with reusable skills, reflection, grounding, contextual policy, optional adaptation
- All phases preserve frozen authority; Brain ends at intent generation

**Serum 2.0.21:**
- [serum2/audit/](serum2/audit/) — 908-record UI census
- [serum2/reference/serum_atlas.py](serum2/reference/serum_atlas.py) — canonical control names + aliases

---

## Quick Start (Developers)

1. Read [FREEZE_VLP1.md](FREEZE_VLP1.md) (1 min) — architecture is frozen
2. Read [BRAIN_B1_PLAN.md](BRAIN_B1_PLAN.md) (5 min) — what B1 does
3. Run baseline: `cd serum2/data/runs/2c0h3z41K58 && python coverage_analysis.py`
4. Measure before/after on the same 9 events
5. Commit atomically with clear intent/measurement

---

## License & Attribution

**VLP-1 Architecture:** Frozen 2026-09-19  
**Implementation:** Claude Code + subject matter expertise  
**Fresh Run Analysis:** 2c0h3z41K58 (YouTube tutorial)

---

**Status:** Architecture frozen. Brain development phase B1 begins.  
**Next:** Read [BRAIN_B1_PLAN.md](BRAIN_B1_PLAN.md) and implement B1.1–B1.6.
