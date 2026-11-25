"""MonitorAgent — first node in the LangGraph recovery pipeline.

Responsibilities:
  1. Health-check all three simulated services.
  2. Identify which services are unhealthy (affected_services).
  3. If anomalies found, optionally call LLM for a human-readable summary.
  4. Return partial RecoveryState dict for LangGraph to merge.
"""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel

from backend.agents.tools.health_check import HealthResult, check_all_services
from backend.graph.base_agent import BaseAgent
from backend.graph.state import RecoveryState


class MonitorSummarySchema(BaseModel):
    anomaly_description: str
    urgency: Literal["critical", "high", "medium", "low"]


_ALL_SERVICES = [
    "resilience-web-server",
    "resilience-database",
    "resilience-backup-store",
]


class MonitorAgent(BaseAgent):
    name = "monitor"

    def run(self, state: RecoveryState) -> dict:
        t0 = time.time()

        results: dict[str, HealthResult] = check_all_services()

        health_metrics: dict[str, dict] = {
            svc: {"healthy": r.healthy, "status": r.status, "error": r.error}
            for svc, r in results.items()
        }

        affected: list[str] = [
            svc for svc, r in results.items() if not r.healthy
        ]
        anomaly_detected = bool(affected)

        anomaly_description = ""
        if anomaly_detected:
            prompt = _build_prompt(affected, health_metrics, state.get("scenario", ""))
            llm_out: MonitorSummarySchema = self._call_llm(prompt, MonitorSummarySchema)
            anomaly_description = llm_out.anomaly_description

        output = {
            "affected_services": affected,
            "health_metrics": health_metrics,
            "anomaly_detected": anomaly_detected,
            "anomaly_description": anomaly_description,
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
        "Service health check results:",
    ]
    for svc, m in metrics.items():
        lines.append(f"  {svc}: healthy={m['healthy']}, status={m['status']}")
    lines += [
        "",
        f"Affected services: {', '.join(affected)}",
        "",
        "Provide a concise anomaly description and urgency level.",
    ]
    return "\n".join(lines)
