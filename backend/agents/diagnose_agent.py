"""DiagnoseAgent — second node in the LangGraph recovery pipeline.

Responsibilities:
  1. Build a prompt from affected_services + health_metrics + scenario.
  2. Call LLM to classify root_cause, severity, confidence.
  3. Retry once on bad LLM output; fall back to root_cause="unknown".
  4. Return partial RecoveryState dict.
"""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel

from backend.graph.base_agent import BaseAgent
from backend.graph.state import RecoveryState


class DiagnosisSchema(BaseModel):
    root_cause: Literal[
        "container_crash",
        "oom_kill",
        "database_connection_lost",
        "disk_full",
        "network_partition",
        "process_hang",
        "config_corruption",
        "cascading_failure",
        "unknown",
    ]
    severity: Literal["critical", "high", "medium", "low"]
    diagnosis_confidence: float   # 0.0 – 1.0
    reasoning: str


_FALLBACK_DIAGNOSIS = DiagnosisSchema(
    root_cause="unknown",
    severity="medium",
    diagnosis_confidence=0.0,
    reasoning="LLM output could not be parsed; manual investigation required.",
)


class DiagnoseAgent(BaseAgent):
    name = "diagnose"

    def run(self, state: RecoveryState) -> dict:
        t0 = time.time()

        affected = state.get("affected_services", [])
        metrics = state.get("health_metrics", {})
        scenario = state.get("scenario", "unknown")

        prompt = _build_prompt(affected, metrics, scenario)

        try:
            result: DiagnosisSchema = self._call_llm(prompt, DiagnosisSchema)
        except Exception:
            result = _FALLBACK_DIAGNOSIS

        output = {
            "root_cause": result.root_cause,
            "severity": result.severity,
            "diagnosis_confidence": result.diagnosis_confidence,
        }

        self._log_action(state, output, success=True,
                         duration_ms=self._elapsed_ms(t0))
        return output


def _build_prompt(
    affected: list[str],
    metrics: dict[str, dict],
    scenario: str,
) -> str:
    lines = [
        f"Scenario: {scenario}",
        "",
        "Affected services:",
    ]
    for svc in affected:
        m = metrics.get(svc, {})
        lines.append(f"  {svc}: status={m.get('status', '?')}, error={m.get('error', '')}")
    lines += [
        "",
        "All service metrics:",
    ]
    for svc, m in metrics.items():
        lines.append(
            f"  {svc}: healthy={m.get('healthy')}, status={m.get('status')}"
        )
    lines += [
        "",
        "Classify the root cause using exactly one of the allowed values.",
        "Provide severity, diagnosis_confidence (0.0-1.0), and brief reasoning.",
    ]
    return "\n".join(lines)
