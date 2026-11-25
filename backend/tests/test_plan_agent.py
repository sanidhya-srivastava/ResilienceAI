"""Tests for PlanAgent (Unit 8)."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

from backend.agents.plan_agent import PlanAgent
from backend.db.database import Database
from backend.db.models import Incident
from backend.db.repository import IncidentRepository


def _db(tmp_path: Path) -> Database:
    db = Database(str(tmp_path / "test.db"))
    db.init_db()
    with db.connect() as conn:
        IncidentRepository.create(
            conn,
            Incident(
                id="inc-plan-001",
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )
    return db


def _base_state() -> dict:
    return {
        "incident_id": "inc-plan-001",
        "scenario": "server_crash",
        "triggered_at": "2026-11-25T10:00:00Z",
        "replan_count": 0,
        "root_cause": "container_crash",
        "severity": "critical",
        "diagnosis_confidence": 0.95,
    }


def test_plan_selects_strategy(tmp_path: Path) -> None:
    """In MOCK_MODE, plan agent should select 'restart_container'."""
    result = PlanAgent(_db(tmp_path)).run(_base_state())
    assert result["recovery_strategy"] == "restart_container"


def test_plan_includes_steps(tmp_path: Path) -> None:
    result = PlanAgent(_db(tmp_path)).run(_base_state())
    steps = result["recovery_steps"]
    assert isinstance(steps, list)
    assert len(steps) > 0


def test_plan_includes_rto(tmp_path: Path) -> None:
    result = PlanAgent(_db(tmp_path)).run(_base_state())
    assert isinstance(result["estimated_rto_seconds"], int)
    assert result["estimated_rto_seconds"] > 0


def test_plan_excludes_previous_on_replan(tmp_path: Path) -> None:
    """On a replan, the agent must NOT pick the previously tried strategy."""
    db = _db(tmp_path)
    # Simulate a replan — previously used restart_container
    state = {**_base_state(), "replan_count": 1, "recovery_strategy": "restart_container"}
    result = PlanAgent(db).run(state)
    # container_crash has 2 strategies; second should be restore_from_backup
    assert result["recovery_strategy"] != "restart_container"


def test_plan_logs_action(tmp_path: Path) -> None:
    from backend.db.repository import ActionRepository

    db = _db(tmp_path)
    PlanAgent(db).run(_base_state())
    with db.connect() as conn:
        actions = ActionRepository.list_by_incident(conn, "inc-plan-001")
    assert any(a.agent_name == "plan" for a in actions)
