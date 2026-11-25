"""VerifyAgent — fifth (final) node in the LangGraph recovery pipeline.

Responsibilities:
  1. Re-run health checks on affected_services.
  2. Call LLM to judge whether recovery was successful.
  3. If verification failed and replan_count < MAX_REPLANS, set replan_required=True.
  4. Increment replan_count.
"""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, model_validator

from backend.agents.tools.health_check import HealthResult, check_service_health
from backend.graph.base_agent import BaseAgent
from backend.graph.state import RecoveryState


class VerificationSchema(BaseModel):
    verification_passed: bool
    replan_required: bool
    verdict_reasoning: str

    @model_validator(mode="after")
    def _check_replan_consistency(self) -> "VerificationSchema":
        if self.replan_required and self.verification_passed:
            raise ValueError("replan_required=True requires verification_passed=False")
        return self


class VerifyAgent(BaseAgent):
    name = "verify"

    def run(self, state: RecoveryState) -> dict:
        t0 = time.time()

        affected = state.get("affected_services", [])
        strategy = state.get("recovery_strategy", "")

        post_metrics: dict[str, dict] = {}
        for svc in affected:
            r: HealthResult = check_service_health(svc)
            post_metrics[svc] = {"healthy": r.healthy, "status": r.status}

        prompt = _build_prompt(affected, post_metrics, strategy, state.get("scenario", ""))

        try:
            result: VerificationSchema = self._call_llm(prompt, VerificationSchema)
        except Exception:
            # Safe fallback — trigger replan rather than falsely declaring success
            result = VerificationSchema(
                verification_passed=False,
                replan_required=True,
                verdict_reasoning="LLM parse error; triggering replan as precaution",
            )

        output = {
            "verification_passed": result.verification_passed,
            "post_recovery_metrics": post_metrics,
            "replan_required": result.replan_required,
            "verdict_reasoning": result.verdict_reasoning,
            "replan_count": state.get("replan_count", 0) + (1 if result.replan_required else 0),
        }

        self._log_action(state, output, success=result.verification_passed,
                         duration_ms=self._elapsed_ms(t0))
        return output


def _build_prompt(
    affected: list[str],
    post_metrics: dict[str, dict],
    strategy: str,
    scenario: str,
) -> str:
    lines = [
        f"Scenario: {scenario}",
        f"Strategy applied: {strategy}",
        "",
        "Post-recovery health check results:",
    ]
    for svc, m in post_metrics.items():
        lines.append(f"  {svc}: healthy={m['healthy']}, status={m['status']}")
    lines += [
        "",
        "Did recovery succeed? Set verification_passed and replan_required accordingly.",
        "Note: replan_required=True is only valid when verification_passed=False.",
    ]
    return "\n".join(lines)
