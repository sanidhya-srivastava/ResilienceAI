"""GraphRunner — orchestrates a full recovery run and streams agent updates."""
from __future__ import annotations

import os
import time
from collections.abc import Callable

from backend.db.database import Database
from backend.db.models import AgentAction, RecoveryMetrics
from backend.db.repository import ActionRepository, IncidentRepository, MetricsRepository
from backend.graph.mock_responses import MOCK_AGENT_OUTPUTS, MOCK_SCENARIO_SEQUENCES
from backend.graph.state import RecoveryState
from backend.simulator.utils import utcnow


WsCallback = Callable[[str, dict], None]


class GraphRunner:
    """Runs the recovery graph for a single incident.

    In MOCK_MODE the five agents are replaced with pre-built outputs so the
    full pipeline completes instantly without Ollama or Docker.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    # ── Public ─────────────────────────────────────────────────────────────────

    def run(
        self,
        incident_id: str,
        scenario: str,
        triggered_at: str,
        ws_callback: WsCallback | None = None,
    ) -> RecoveryState:
        """Execute the recovery pipeline synchronously and return the final state."""
        if _is_mock_mode():
            return self._run_mock(incident_id, scenario, triggered_at, ws_callback)
        return self._run_real(incident_id, scenario, triggered_at, ws_callback)

    # ── Mock execution (no Ollama / Docker required) ───────────────────────────

    def _run_mock(
        self,
        incident_id: str,
        scenario: str,
        triggered_at: str,
        ws_callback: WsCallback | None,
    ) -> RecoveryState:
        steps = MOCK_SCENARIO_SEQUENCES.get(
            scenario, list(MOCK_AGENT_OUTPUTS.items())
        )

        state: RecoveryState = {
            "incident_id": incident_id,
            "scenario": scenario,
            "triggered_at": triggered_at,
            "replan_count": 0,
        }

        phase_times: dict[str, float] = {}

        for agent_name, template in steps:
            t0 = time.perf_counter()
            partial = dict(template)
            state.update(partial)  # type: ignore[typeddict-item]
            elapsed = max(time.perf_counter() - t0, 0.001)
            phase_times[agent_name] = phase_times.get(agent_name, 0.0) + elapsed

            self._log_mock_action(
                incident_id=incident_id,
                agent_name=agent_name,
                output=partial,
                duration_ms=max(int(elapsed * 1000), 1),
            )

            if ws_callback:
                ws_callback(agent_name, partial)

        state["completed_at"] = utcnow()
        total = sum(phase_times.values())
        state["total_duration_seconds"] = total

        self._persist(state, phase_times, triggered_at)
        return state

    # ── Real execution (Ollama + Docker) ──────────────────────────────────────

    def _run_real(
        self,
        incident_id: str,
        scenario: str,
        triggered_at: str,
        ws_callback: WsCallback | None,
    ) -> RecoveryState:
        from backend.graph.graph import build_recovery_graph  # noqa: PLC0415
        from backend.agents.monitor_agent import MonitorAgent  # noqa: PLC0415
        from backend.agents.diagnose_agent import DiagnoseAgent  # noqa: PLC0415
        from backend.agents.plan_agent import PlanAgent  # noqa: PLC0415
        from backend.agents.recover_agent import RecoverAgent  # noqa: PLC0415
        from backend.agents.verify_agent import VerifyAgent  # noqa: PLC0415

        agents = {
            "monitor": MonitorAgent(self.db),
            "diagnose": DiagnoseAgent(self.db),
            "plan": PlanAgent(self.db),
            "recover": RecoverAgent(self.db),
            "verify": VerifyAgent(self.db),
        }

        graph = build_recovery_graph(agents)
        config = {"configurable": {"thread_id": incident_id}}

        initial_state: RecoveryState = {
            "incident_id": incident_id,
            "scenario": scenario,
            "triggered_at": triggered_at,
            "replan_count": 0,
        }

        phase_times: dict[str, float] = {}
        chunk_start = time.perf_counter()

        for chunk in graph.stream(initial_state, config=config):
            now = time.perf_counter()
            for node_name, partial in chunk.items():
                if node_name == "__end__":
                    continue
                phase_times[node_name] = phase_times.get(node_name, 0.0) + max(now - chunk_start, 0.001)
                if ws_callback:
                    ws_callback(node_name, partial)
            chunk_start = time.perf_counter()

        snapshot = graph.get_state(config)
        final_state: RecoveryState = dict(snapshot.values)  # type: ignore[arg-type]
        final_state["completed_at"] = utcnow()
        total = sum(phase_times.values())
        final_state["total_duration_seconds"] = total

        self._persist(final_state, phase_times, triggered_at)
        return final_state

    # ── Persistence ────────────────────────────────────────────────────────────

    def _log_mock_action(
        self,
        incident_id: str,
        agent_name: str,
        output: dict,
        duration_ms: int,
    ) -> None:
        """Persist a synthetic agent action record during MOCK_MODE runs."""
        try:
            with self.db.connect() as conn:
                ActionRepository.create(
                    conn,
                    AgentAction(
                        incident_id=incident_id,
                        agent_name=agent_name,
                        action_type="execute",
                        output_summary=str(output)[:500],
                        success=True,
                        duration_ms=duration_ms,
                        timestamp=utcnow(),
                    ),
                )
        except Exception:
            pass

    def _persist(
        self,
        state: RecoveryState,
        phase_times: dict[str, float],
        triggered_at: str,
    ) -> None:
        success = bool(state.get("verification_passed", False))
        status = "recovered" if success else "failed"

        with self.db.connect() as conn:
            IncidentRepository.update_status(
                conn,
                incident_id=state["incident_id"],
                status=status,
                completed_at=state.get("completed_at"),
                total_duration_seconds=state.get("total_duration_seconds"),
            )
            MetricsRepository.upsert(
                conn,
                RecoveryMetrics(
                    incident_id=state["incident_id"],
                    mttr_seconds=state.get("total_duration_seconds"),
                    detection_time_seconds=phase_times.get("monitor"),
                    diagnosis_time_seconds=phase_times.get("diagnose"),
                    planning_time_seconds=phase_times.get("plan"),
                    recovery_time_seconds=phase_times.get("recover"),
                    verification_time_seconds=phase_times.get("verify"),
                    replan_count=state.get("replan_count", 0),
                    recovery_strategy=state.get("recovery_strategy"),
                    success=success,
                ),
            )


def _is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").lower() == "true"
