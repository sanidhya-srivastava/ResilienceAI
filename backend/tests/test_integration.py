"""End-to-end integration tests for the recovery pipeline (MOCK_MODE)."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

from backend.db.database import Database
from backend.db.models import Incident
from backend.db.repository import (
    ActionRepository,
    IncidentRepository,
    MetricsRepository,
)
from backend.graph.base_agent import BaseAgent
from backend.graph.graph import MAX_REPLANS, build_recovery_graph
from backend.graph.runner import GraphRunner
from backend.graph.state import RecoveryState
from backend.simulator.scenarios import ScenarioRegistry


def _init_db(tmp_path: Path, incident_id: str) -> Database:
    db = Database(str(tmp_path / "integration.db"))
    db.init_db()
    with db.connect() as conn:
        IncidentRepository.create(
            conn,
            Incident(
                id=incident_id,
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )
    return db


def test_full_recovery_pipeline_persists_actions_and_metrics(tmp_path: Path) -> None:
    """Trigger scenario -> GraphRunner completes -> SQLite has 5 actions + metrics."""
    incident_id = "inc-int-001"
    db = _init_db(tmp_path, incident_id)

    injection = ScenarioRegistry.get("server_crash").inject()
    assert injection.success is True

    events: list[str] = []
    final_state = GraphRunner(db).run(
        incident_id=incident_id,
        scenario="server_crash",
        triggered_at="2026-11-25T10:00:00Z",
        ws_callback=lambda name, _partial: events.append(name),
    )

    assert events == ["monitor", "diagnose", "plan", "recover", "verify"]
    assert final_state["verification_passed"] is True

    with db.connect() as conn:
        incident = IncidentRepository.get_by_id(conn, incident_id)
        actions = ActionRepository.list_by_incident(conn, incident_id)
        metrics = MetricsRepository.get_by_incident(conn, incident_id)

    assert incident is not None
    assert incident.status == "recovered"
    assert [a.agent_name for a in actions] == [
        "monitor",
        "diagnose",
        "plan",
        "recover",
        "verify",
    ]
    assert metrics is not None
    assert metrics.success is True
    assert metrics.mttr_seconds is not None and metrics.mttr_seconds > 0
    assert metrics.recovery_strategy == "restart_container"


def test_replan_loop_recovers_after_two_failures() -> None:
    """Verify node triggers replan twice and passes on the 3rd attempt."""
    plan_calls = 0

    class StubAgent(BaseAgent):
        def __init__(self, name: str, fn):
            self.name = name
            self.db = None  # type: ignore[assignment]
            self._fn = fn

        def run(self, state: RecoveryState) -> dict:
            return self._fn(state)

    def _plan(_state: RecoveryState) -> dict:
        nonlocal plan_calls
        plan_calls += 1
        return {
            "recovery_strategy": "restart_container" if plan_calls == 1 else "restore_from_backup",
            "recovery_steps": ["step 1"],
            "estimated_rto_seconds": 30,
        }

    def _verify(state: RecoveryState) -> dict:
        count = state.get("replan_count", 0)
        if count < 2:
            return {
                "verification_passed": False,
                "replan_required": True,
                "replan_count": count + 1,
            }
        return {
            "verification_passed": True,
            "replan_required": False,
            "replan_count": count,
        }

    agents = {
        "monitor": StubAgent("monitor", lambda _s: {"anomaly_detected": True}),
        "diagnose": StubAgent("diagnose", lambda _s: {"root_cause": "container_crash"}),
        "plan": StubAgent("plan", _plan),
        "recover": StubAgent("recover", lambda _s: {"recovery_success": True}),
        "verify": StubAgent("verify", _verify),
    }

    compiled = build_recovery_graph(agents)
    result = compiled.invoke(
        {
            "incident_id": "inc-replan-001",
            "scenario": "server_crash",
            "triggered_at": "2026-11-25T10:00:00Z",
            "replan_count": 0,
        },
        config={"configurable": {"thread_id": "inc-replan-001"}},
    )

    assert plan_calls == 3
    assert result["verification_passed"] is True
    assert result["replan_count"] == 2


def test_max_replan_guard_stops_infinite_loop() -> None:
    """Graph stops cleanly once replan_count reaches MAX_REPLANS even if verify keeps failing."""

    class AlwaysFailVerify(BaseAgent):
        name = "verify"

        def __init__(self) -> None:
            self.db = None  # type: ignore[assignment]

        def run(self, state: RecoveryState) -> dict:
            return {
                "verification_passed": False,
                "replan_required": True,
                "replan_count": state.get("replan_count", 0) + 1,
            }

    class NoopAgent(BaseAgent):
        def __init__(self, name: str) -> None:
            self.name = name
            self.db = None  # type: ignore[assignment]

        def run(self, _state: RecoveryState) -> dict:
            return {}

    compiled = build_recovery_graph(
        {
            "monitor": NoopAgent("monitor"),
            "diagnose": NoopAgent("diagnose"),
            "plan": NoopAgent("plan"),
            "recover": NoopAgent("recover"),
            "verify": AlwaysFailVerify(),
        }
    )

    result = compiled.invoke(
        {
            "incident_id": "inc-guard-001",
            "scenario": "server_crash",
            "triggered_at": "2026-11-25T10:00:00Z",
            "replan_count": 0,
        },
        config={"configurable": {"thread_id": "inc-guard-001"}},
    )

    assert result["verification_passed"] is False
    assert result["replan_count"] == MAX_REPLANS
