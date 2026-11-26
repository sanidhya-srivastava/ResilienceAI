"""RecoverAgent — fourth node in the LangGraph recovery pipeline.

Purely deterministic — no LLM call.
Executes the strategy selected by PlanAgent using Docker operation tools.
"""
from __future__ import annotations

import time
from collections.abc import Callable

from backend.agents.tools.docker_ops import (
    OpResult,
    cleanup_disk,
    restart_container,
    restore_from_backup,
)
from backend.graph.base_agent import BaseAgent
from backend.graph.state import RecoveryState

# Maps strategy name → handler function(affected_services) → list[OpResult]
StrategyHandler = Callable[[list[str]], list[OpResult]]


def _handle_restart(affected: list[str]) -> list[OpResult]:
    return [restart_container(svc) for svc in affected]


def _handle_restore(affected: list[str]) -> list[OpResult]:
    results = []
    for svc in affected:
        results.append(restore_from_backup(svc))
        results.append(restart_container(svc))
    return results


def _handle_cleanup_disk(affected: list[str]) -> list[OpResult]:
    return [cleanup_disk(svc) for svc in affected]


def _handle_ordered_recovery(affected: list[str]) -> list[OpResult]:
    """Recover database dependencies before application containers."""
    db_first = sorted(affected, key=lambda s: (0 if "database" in s else 1, s))
    return [restart_container(svc) for svc in db_first]


STRATEGY_HANDLERS: dict[str, StrategyHandler] = {
    "restart_container": _handle_restart,
    "restore_from_backup": _handle_restore,
    "cleanup_disk": _handle_cleanup_disk,
    "ordered_recovery": _handle_ordered_recovery,
}


class RecoverAgent(BaseAgent):
    name = "recover"

    def run(self, state: RecoveryState) -> dict:
        t0 = time.time()

        strategy = state.get("recovery_strategy", "restart_container")
        affected = state.get("affected_services", [])

        handler = STRATEGY_HANDLERS.get(strategy, _handle_restart)
        op_results: list[OpResult] = handler(affected)

        actions_taken = [
            {
                "action": f"{r.action}:{r.service}",
                "timestamp": r.timestamp,
                "success": r.success,
                "detail": r.detail,
            }
            for r in op_results
        ]

        overall_success = all(r.success for r in op_results)

        output = {
            "actions_taken": actions_taken,
            "recovery_attempted": True,
            "recovery_success": overall_success,
        }

        self._log_action(state, output, success=overall_success,
                         duration_ms=self._elapsed_ms(t0))
        return output
