"""Tests for RecoverAgent (Unit 9)."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

from backend.agents.recover_agent import RecoverAgent
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
                id="inc-rec-001",
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )
    return db


def _base_state(strategy: str = "restart_container") -> dict:
    return {
        "incident_id": "inc-rec-001",
        "scenario": "server_crash",
        "triggered_at": "2026-11-25T10:00:00Z",
        "replan_count": 0,
        "affected_services": ["resilience-web-server"],
        "recovery_strategy": strategy,
        "recovery_steps": ["Restart container", "Verify health"],
        "estimated_rto_seconds": 30,
    }


def test_recover_restart_succeeds_in_mock(tmp_path: Path) -> None:
    """In MOCK_MODE, restart_container strategy always succeeds."""
    result = RecoverAgent(_db(tmp_path)).run(_base_state("restart_container"))
    assert result["recovery_success"] is True
    assert result["recovery_attempted"] is True


def test_recover_restore_succeeds_in_mock(tmp_path: Path) -> None:
    """In MOCK_MODE, restore_from_backup strategy always succeeds."""
    result = RecoverAgent(_db(tmp_path)).run(_base_state("restore_from_backup"))
    assert result["recovery_success"] is True


def test_recover_actions_taken_nonempty(tmp_path: Path) -> None:
    result = RecoverAgent(_db(tmp_path)).run(_base_state())
    assert isinstance(result["actions_taken"], list)
    assert len(result["actions_taken"]) > 0


def test_recover_action_has_required_keys(tmp_path: Path) -> None:
    result = RecoverAgent(_db(tmp_path)).run(_base_state())
    action = result["actions_taken"][0]
    for key in ("action", "timestamp", "success", "detail"):
        assert key in action, f"Missing key '{key}' in action dict"


def test_recover_logs_action(tmp_path: Path) -> None:
    from backend.db.repository import ActionRepository

    db = _db(tmp_path)
    RecoverAgent(db).run(_base_state())
    with db.connect() as conn:
        actions = ActionRepository.list_by_incident(conn, "inc-rec-001")
    assert any(a.agent_name == "recover" for a in actions)
