"""PlanAgent — third node in the LangGraph recovery pipeline.

Responsibilities:
  1. Look up valid strategies for the diagnosed root_cause.
  2. If replanning, exclude the previously tried strategy from the prompt.
  3. Call LLM to select the best strategy.
  4. Return recovery_strategy, recovery_steps, estimated_rto_seconds.
"""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel

from backend.agents.strategies import RecoveryStrategy, get_strategies_for
from backend.graph.base_agent import BaseAgent
from backend.graph.state import RecoveryState


class PlanningSchema(BaseModel):
    selected_strategy: str   # must be one of the offered names
    rationale: str
    confidence: float        # 0.0 – 1.0


class PlanAgent(BaseAgent):
    name = "plan"

    def run(self, state: RecoveryState) -> dict:
        t0 = time.time()

        root_cause = state.get("root_cause", "unknown")
        replan_count = state.get("replan_count", 0)
        previous_strategy = state.get("recovery_strategy")  # None on first pass

        strategies = get_strategies_for(root_cause)

        # Exclude the previously tried strategy on replans
        if replan_count > 0 and previous_strategy:
            strategies = [s for s in strategies if s.name != previous_strategy]
        if not strategies:
            # All strategies exhausted — fall back to restore_from_backup
            from backend.agents.strategies import STRATEGY_CATALOG  # noqa: PLC0415
            strategies = STRATEGY_CATALOG["unknown"]

        prompt = _build_prompt(root_cause, strategies, replan_count, previous_strategy)

        try:
            result: PlanningSchema = self._call_llm(prompt, PlanningSchema)
            # Validate the selection is actually in the offered list
            valid_names = {s.name for s in strategies}
            if result.selected_strategy not in valid_names:
                result.selected_strategy = strategies[0].name
        except Exception:
            result = PlanningSchema(
                selected_strategy=strategies[0].name,
                rationale="Fallback to first available strategy after LLM error",
                confidence=0.5,
            )

        chosen: RecoveryStrategy = next(
            (s for s in strategies if s.name == result.selected_strategy),
            strategies[0],
        )

        output = {
            "recovery_strategy": chosen.name,
            "recovery_steps": chosen.steps,
            "estimated_rto_seconds": chosen.estimated_rto_seconds,
        }

        self._log_action(state, output, success=True,
                         duration_ms=self._elapsed_ms(t0))
        return output


def _build_prompt(
    root_cause: str,
    strategies: list[RecoveryStrategy],
    replan_count: int,
    previous_strategy: str | None,
) -> str:
    lines = [
        f"Root cause: {root_cause}",
        f"Replan attempt: {replan_count}",
    ]
    if previous_strategy:
        lines.append(f"Previously tried strategy (do NOT select): {previous_strategy}")
    lines += ["", "Available recovery strategies:"]
    for s in strategies:
        lines.append(f"  - {s.name} (estimated RTO: {s.estimated_rto_seconds}s)")
        for step in s.steps:
            lines.append(f"      • {step}")
    lines += [
        "",
        "Select the best strategy. Return selected_strategy (exact name), rationale, confidence.",
    ]
    return "\n".join(lines)
