"""16.5.61b: Planner — Claude reasoning at the decision boundary.

Reads GoalGroundingResult and evidence system, invokes Claude Code to select
among admissible capabilities, outputs Plan.

Claude Code is the reasoning brain.
Evidence system is the capability authority.

Decision process per gap type:

  SATISFIED      → no action; goal already met
  MISSING        → collect admissible capabilities → Claude selects → PlannedAction
  CONTRADICTORY  → collect corrective capabilities → Claude selects → PlannedAction
  CONSTRAINED    → check if constraint lifts; if not → BlockedGap
  UNGROUNDED     → DiscoveryRequest

Invariants:

  1. Planner chooses what, not how. Output is intent-level, not parameter-level.
     Example: "increase_bass_brightness" (intent)
     NOT: "set Filter.Cutoff to 0.7" (parameter)

  2. Claude selects among admissible candidates only.
     Claude cannot invent capabilities or alter evidence system authority.

  3. Evidence system is authoritative.
     Only capabilities with CAUSAL_VERIFIED status (or specified lower status)
     are presented to Claude as admissible.

  4. Retrieval is decision input, not authority.
     Retrieved episodes inform Claude's reasoning but do not authorize execution.

  5. Planner decision is auditable.
     Every PlannedAction names the gap it addresses, the capability it chose,
     the evidence status, and Claude's rationale.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .goal_grounding import GoalGroundingResult, CharacteristicGap, GapType
from .goal_model import GoalModel


@dataclass(frozen=True)
class PlannedAction:
    """One intentional action the Planner decided to execute.

    intent: human-readable action (e.g., "darken_bass", "increase_punchiness")
    target_dimension: musical dimension being addressed (e.g., "brightness", "attack")
    gap: the CharacteristicGap this action addresses
    selected_capability: semantic_target_name chosen to address the gap
    capability_key: capability_key from the evidence system (for audit)
    capability_status: CAUSAL_VERIFIED | STRUCTURAL_ONLY | HYPOTHESIS | UNGROUNDED
    reasoning: why this capability was chosen (e.g., "CAUSAL_VERIFIED, metric=centroid")
    """
    intent: str
    target_dimension: str
    gap: CharacteristicGap
    selected_capability: str
    capability_key: str
    capability_status: str
    reasoning: str


@dataclass(frozen=True)
class BlockedGap:
    """A gap the Planner could not resolve.

    gap: the CharacteristicGap that couldn't be addressed
    reason: why it's blocked (e.g., "no qualified capability", "constraint prevents action")
    detail: additional context
    """
    gap: CharacteristicGap
    reason: str
    detail: str


@dataclass(frozen=True)
class DiscoveryRequest:
    """Request for new evidence to support a goal.

    gap: the CharacteristicGap that is ungrounded
    reason: why discovery is needed
    candidate_targets: which semantic targets *might* address this
                       (caller must design isolated experiment)
    """
    gap: CharacteristicGap
    reason: str
    candidate_targets: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Plan:
    """Decision output from Planner.

    goal: the original GoalModel
    grounding: the GoalGroundingResult analyzed
    actions: PlannedActions to execute (musical intent level, not parameters)
    blocked_gaps: gaps the Planner could not resolve
    discovery_requests: gaps requiring new evidence
    confidence: "grounded" (all CAUSAL_VERIFIED), "bounded" (mix), "low" (contains HYPOTHESIS)
    """
    goal: GoalModel
    grounding: GoalGroundingResult
    confidence: str
    actions: List[PlannedAction] = field(default_factory=list)
    blocked_gaps: List[BlockedGap] = field(default_factory=list)
    discovery_requests: List[DiscoveryRequest] = field(default_factory=list)

    @property
    def is_executable(self) -> bool:
        """True if plan has no blocking gaps and no discovery requests."""
        return not (self.blocked_gaps or self.discovery_requests)

    @property
    def has_refusals(self) -> bool:
        """True if plan contains any refusals (blocked or discovery)."""
        return bool(self.blocked_gaps or self.discovery_requests)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for audit."""
        return {
            "goal": self.goal.to_dict(),
            "planned_actions": len(self.actions),
            "blocked_gaps": len(self.blocked_gaps),
            "discovery_requests": len(self.discovery_requests),
            "is_executable": self.is_executable,
            "confidence": self.confidence,
            "actions": [
                {
                    "intent": a.intent,
                    "dimension": a.target_dimension,
                    "capability": a.selected_capability,
                    "status": a.capability_status,
                    "reasoning": a.reasoning,
                }
                for a in self.actions
            ],
            "blocked": [
                {
                    "dimension": b.gap.characteristic_name,
                    "reason": b.reason,
                    "detail": b.detail,
                }
                for b in self.blocked_gaps
            ],
            "discoveries": [
                {
                    "dimension": d.gap.characteristic_name,
                    "reason": d.reason,
                    "candidates": d.candidate_targets,
                }
                for d in self.discovery_requests
            ],
        }


class PlannerDecisionEngine:
    """Planner that reads GoalGroundingResult and evidence system, outputs Plan.

    Caller supplies:
      - grounding: GoalGroundingResult (goal vs. world state analysis)
      - evidence_system: object with capabilities() query method
      - allowed_statuses: list of CapabilityContract.status values to accept
                          (default: ["CAUSAL_VERIFIED"] for fully grounded)

    Planner decides:
      - SATISFIED gaps → skip (goal already met)
      - MISSING gaps → find capability → PlannedAction
      - CONTRADICTORY gaps → find corrective capability OR BlockedGap
      - CONSTRAINED gaps → BlockedGap (prerequisites block execution)
      - UNGROUNDED gaps → DiscoveryRequest
    """

    def __init__(
        self,
        evidence_system: Any,
        allowed_statuses: Optional[List[str]] = None,
    ):
        """Initialize the Planner.

        evidence_system: object that can answer queries like:
          - evidence_system.get_capability(semantic_target_name, dimension)
          - evidence_system.get_contracts_for_dimension(dimension)

        allowed_statuses: which CapabilityContract.status values are acceptable
                         (default: ["CAUSAL_VERIFIED"])
                         To allow bounded/exploratory: ["CAUSAL_VERIFIED", "STRUCTURAL_ONLY"]
        """
        self.evidence_system = evidence_system
        self.allowed_statuses = allowed_statuses or ["CAUSAL_VERIFIED"]

    def plan(
        self,
        grounding: GoalGroundingResult,
        retrieved_episodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Plan:
        """Convert GoalGroundingResult into an executable Plan.

        Args:
            grounding: GoalGroundingResult with gaps and goal analysis
            retrieved_episodes: optional list of retrieved episodes to inform reasoning

        Returns Plan with actions, blocked_gaps, and discovery_requests.
        """
        actions = []
        blocked_gaps = []
        discovery_requests = []
        confidences = []

        goal = grounding.goal
        retrieved_episodes = retrieved_episodes or []

        # ---- SATISFIED gaps: no action needed ----
        for gap in grounding.satisfied:
            # Confidence boost: goal is already met
            pass

        # ---- MISSING gaps: find capability ----
        for gap in grounding.missing:
            decision = self._plan_missing_gap(
                gap,
                goal=goal,
                retrieved_episodes=retrieved_episodes,
            )
            if isinstance(decision, PlannedAction):
                actions.append(decision)
                confidences.append(decision.capability_status)
            elif isinstance(decision, DiscoveryRequest):
                discovery_requests.append(decision)
            elif isinstance(decision, BlockedGap):
                blocked_gaps.append(decision)

        # ---- CONTRADICTORY gaps: find corrective capability ----
        for gap in grounding.contradictory:
            decision = self._plan_contradictory_gap(gap)
            if isinstance(decision, PlannedAction):
                actions.append(decision)
                confidences.append(decision.capability_status)
            elif isinstance(decision, DiscoveryRequest):
                discovery_requests.append(decision)
            elif isinstance(decision, BlockedGap):
                blocked_gaps.append(decision)

        # ---- CONSTRAINED gaps: cannot execute ----
        for gap in grounding.constrained:
            blocked_gaps.append(BlockedGap(
                gap=gap,
                reason="CONSTRAINED",
                detail=gap.detail,
            ))

        # ---- UNGROUNDED gaps: discovery request ----
        for gap in grounding.ungrounded:
            discovery_requests.append(DiscoveryRequest(
                gap=gap,
                reason="UNGROUNDED",
                candidate_targets=gap.possible_capabilities or [],
            ))

        # Determine confidence
        confidence = self._determine_confidence(confidences)

        return Plan(
            goal=goal,
            grounding=grounding,
            actions=actions,
            blocked_gaps=blocked_gaps,
            discovery_requests=discovery_requests,
            confidence=confidence,
        )

    def _plan_missing_gap(
        self,
        gap: CharacteristicGap,
        goal: "GoalModel" = None,
        retrieved_episodes: Optional[List[Dict[str, Any]]] = None,
    ) -> "PlannedAction | BlockedGap | DiscoveryRequest":
        """Decide how to address a MISSING gap using Claude reasoning.

        MISSING gaps do NOT have a current contradiction. The characteristic
        is either not measured or unmeasured.

        Process:
          1. Collect all capabilities from gap.possible_capabilities that match allowed_statuses
          2. Build (target, direction, magnitude) candidates within authority-derived scope
          3. If none found → DiscoveryRequest
          4. If found → pass admissible candidates to Claude Code for selection
          5. Claude selects by index from the magnitude-constrained grid
          6. Validate Claude's selection against admissible set
          7. Return PlannedAction with Claude's rationale and selected magnitude
        """
        if not gap.possible_capabilities:
            # No known capability for this gap
            return DiscoveryRequest(
                gap=gap,
                reason="NO_KNOWN_CAPABILITY",
                candidate_targets=[],
            )

        # ---- COLLECT ADMISSIBLE CANDIDATES WITH MAGNITUDE GRID ----
        admissible_candidates = []
        selected_magnitude = None  # Will be extracted from Claude's selection

        for semantic_target in gap.possible_capabilities:
            contract = self.evidence_system.get_capability(semantic_target)
            if contract is None:
                continue

            contract_status = getattr(contract, "status", "UNKNOWN")
            if contract_status not in self.allowed_statuses:
                continue

            # Build (target, direction, magnitude) candidates
            # Direction: derived from goal intent vs current value
            # (For now, assume increase-direction for "longer", "more", "increase", etc.)
            direction = 1  # Increase direction (from goal semantics)

            # Scope and magnitude candidates: authority-derived from contract or context
            # TEMPORARY: hard-coded for Env1.Release per Step 3.0/3.2 spec
            # Later: derive from contract.prerequisites or context requirements
            if semantic_target == "Env1.Release":
                scope_min, scope_max = 0.50, 0.80
                current_value = 0.50  # From Step 3.0 spec
                magnitude_steps = [0.03, 0.05, 0.08]  # Authority-constrained grid

                for magnitude in magnitude_steps:
                    resultant = current_value + magnitude
                    if scope_min <= resultant <= scope_max:
                        admissible_candidates.append({
                            "target": semantic_target,
                            "direction": direction,
                            "magnitude": magnitude,
                            "resultant": resultant,
                            "status": contract_status,
                            "reason": f"{contract_status} contract; magnitude {magnitude:+.2f} in scope [{scope_min}, {scope_max}]",
                            "source": "capability",
                        })
            else:
                # For other targets, build target-only candidates (no magnitude grid yet)
                admissible_candidates.append({
                    "target": semantic_target,
                    "direction": direction,
                    "status": contract_status,
                    "reason": f"{contract_status} contract available",
                    "source": "capability",
                })

        if not admissible_candidates:
            # No qualified capability found
            return DiscoveryRequest(
                gap=gap,
                reason="NO_QUALIFIED_CAPABILITY",
                candidate_targets=gap.possible_capabilities,
            )

        # ---- RETRIEVE RELEVANT EPISODES ----
        relevant_episodes = []
        if retrieved_episodes is None:
            # If no episodes provided at call time, retrieve from storage
            from .episode_retrieval import retrieve_relevant_episodes
            try:
                relevant_episodes = retrieve_relevant_episodes(
                    semantic_target=gap.characteristic_name,
                    intent=goal.intent if goal and hasattr(goal, 'intent') else None,
                    learning_eligible_only=True,
                )
            except Exception:
                # Retrieval failure is not fatal; continue without episodes
                relevant_episodes = []
        else:
            # Use provided episodes (from parameter)
            relevant_episodes = retrieved_episodes

        # ---- INVOKE CLAUDE FOR SELECTION ----
        try:
            from .claude_reasoning import invoke_claude_for_selection

            goal_intent = goal.intent if goal and hasattr(goal, 'intent') else str(goal) if goal else "unknown"
            claude_decision = invoke_claude_for_selection(
                goal_intent=goal_intent,
                semantic_target=gap.characteristic_name,
                admissible_candidates=admissible_candidates,
                retrieved_episodes=relevant_episodes,
                context={
                    "characteristic": gap.characteristic_name,
                    "goal_value": str(gap.goal_value),
                    "current_value": str(gap.current_value) if gap.current_value else "unmeasured",
                },
            )
        except Exception as e:
            # If Claude reasoning fails, return discovery request
            return DiscoveryRequest(
                gap=gap,
                reason=f"CLAUDE_REASONING_FAILED: {str(e)}",
                candidate_targets=gap.possible_capabilities,
            )

        # ---- VALIDATE AND EXTRACT SELECTED MAGNITUDE ----
        selected_idx = claude_decision.selected
        if selected_idx < 0 or selected_idx >= len(admissible_candidates):
            raise ValueError(
                f"Claude selected index {selected_idx} out of range [0, {len(admissible_candidates)-1}]"
            )

        selected_candidate_dict = admissible_candidates[selected_idx]
        selected_target = selected_candidate_dict["target"]
        selected_magnitude = selected_candidate_dict.get("magnitude")

        # Verify selected target is in admissible set
        admissible_targets = {c["target"]: c for c in admissible_candidates}
        if selected_target not in admissible_targets:
            raise ValueError(
                f"Claude selected inadmissible target '{selected_target}'. "
                f"Admissible: {list(admissible_targets.keys())}"
            )

        admissible_cand = selected_candidate_dict
        contract = self.evidence_system.get_capability(selected_target)
        capability_key = getattr(contract, "target", selected_target) if contract else selected_target

        intent = self._intent_for_gap(gap)

        # Construct reasoning string with magnitude if available
        reasoning = claude_decision.rationale
        if selected_magnitude is not None:
            reasoning = f"{claude_decision.rationale} [magnitude: +{selected_magnitude:.2f}]"

        return PlannedAction(
            intent=intent,
            target_dimension=gap.characteristic_name,
            gap=gap,
            selected_capability=selected_target,
            capability_key=capability_key,
            capability_status=admissible_cand["status"],
            reasoning=reasoning,
        )

    def _plan_contradictory_gap(self, gap: CharacteristicGap) -> "PlannedAction | BlockedGap | DiscoveryRequest":
        """Decide how to address a CONTRADICTORY gap (goal conflicts with current state).

        CONTRADICTORY means:
          - Goal requires value A
          - World state shows value B
          - A ≠ B (or A > B or A < B)

        Decision:
          1. Find a capability that moves in the correction direction
          2. If found and qualified → PlannedAction with "corrective" intent
          3. If not found or not qualified → BlockedGap (cannot proceed)
        """
        if not gap.possible_capabilities:
            return BlockedGap(
                gap=gap,
                reason="CONTRADICTORY_NO_CORRECTION",
                detail="Goal contradicts current state, but no known capability can correct it",
            )

        # Try to find a corrective capability
        # For now, assume the first possible_capability is the corrective one.
        # (In practice, this would be more nuanced based on measurement direction.)
        for semantic_target in gap.possible_capabilities:
            contract = self.evidence_system.get_capability(semantic_target)
            if contract is None:
                continue

            contract_status = getattr(contract, "status", "UNKNOWN")
            if contract_status not in self.allowed_statuses:
                continue

            # Found a corrective capability
            intent = self._intent_for_corrective_gap(gap)
            return PlannedAction(
                intent=intent,
                target_dimension=gap.characteristic_name,
                gap=gap,
                selected_capability=semantic_target,
                capability_key=getattr(contract, "target", semantic_target),
                capability_status=contract_status,
                reasoning=f"{contract_status}; reversing current {gap.current_value} to meet goal {gap.goal_value}",
            )

        # No qualified capability found
        return BlockedGap(
            gap=gap,
            reason="CONTRADICTORY_NO_QUALIFIED_CORRECTION",
            detail=(
                f"Goal {gap.goal_value} contradicts current {gap.current_value}; "
                f"no qualified capability found to correct it"
            ),
        )

    def _intent_for_gap(self, gap: CharacteristicGap) -> str:
        """Generate an intent string for a MISSING gap.

        Examples:
          - "darken_bass" (characteristic_name=brightness, goal_value=dark)
          - "increase_punchiness" (characteristic_name=attack, goal_value=punchy)
        """
        dim = gap.characteristic_name.replace(":", "_").replace(" ", "_")
        goal = str(gap.goal_value).replace(" ", "_")
        return f"{dim}_{goal}"

    def _intent_for_corrective_gap(self, gap: CharacteristicGap) -> str:
        """Generate an intent string for a CONTRADICTORY gap.

        Examples:
          - "correct_bass_brightness_from_bright_to_dark"
        """
        dim = gap.characteristic_name.replace(":", "_").replace(" ", "_")
        from_val = str(gap.current_value).replace(" ", "_")
        to_val = str(gap.goal_value).replace(" ", "_")
        return f"correct_{dim}_from_{from_val}_to_{to_val}"

    def _determine_confidence(self, statuses: List[str]) -> str:
        """Determine overall confidence level.

        "grounded" if all actions are CAUSAL_VERIFIED
        "bounded" if mix of CAUSAL_VERIFIED and STRUCTURAL_ONLY
        "low" if any HYPOTHESIS
        """
        if not statuses:
            return "unknown"
        if all(s == "CAUSAL_VERIFIED" for s in statuses):
            return "grounded"
        if "HYPOTHESIS" in statuses:
            return "low"
        if "STRUCTURAL_ONLY" in statuses and "CAUSAL_VERIFIED" in statuses:
            return "bounded"
        if all(s == "STRUCTURAL_ONLY" for s in statuses):
            return "structural"
        return "unknown"
