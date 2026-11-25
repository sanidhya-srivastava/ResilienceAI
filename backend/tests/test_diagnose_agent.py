"""Tests for DiagnoseAgent (Unit 7)."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

from backend.agents.diagnose_agent import DiagnoseAgent
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
                id="inc-diag-001",
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )
    return db


def _base_state() -> dict:
    return {
        "incident_id": "inc-diag-001",
        "scenario": "server_crash",
        "triggered_at": "2026-11-25T10:00:00Z",
        "replan_count": 0,
        "affected_services": ["resilience-web-server"],
        "health_metrics": {
            "resilience-web-server": {"healthy": False, "status": "exited", "error": ""},
            "resilience-database": {"healthy": True, "status": "running", "error": ""},
            "resilience-backup-store": {"healthy": True, "status": "running", "error": ""},
        },
    }


def test_diagnose_returns_root_cause(tmp_path: Path) -> None:
    """In MOCK_MODE, root_cause should be 'container_crash'."""
    agent = DiagnoseAgent(_db(tmp_path))
    result = agent.run(_base_state())
    assert result["root_cause"] == "container_crash"


def test_diagnose_returns_severity(tmp_path: Path) -> None:
    agent = DiagnoseAgent(_db(tmp_path))
    result = agent.run(_base_state())
    assert result["severity"] in ("critical", "high", "medium", "low")


def test_diagnose_confidence_in_range(tmp_path: Path) -> None:
    agent = DiagnoseAgent(_db(tmp_path))
    result = agent.run(_base_state())
    conf = result["diagnosis_confidence"]
    assert 0.0 <= conf <= 1.0


def test_diagnose_logs_action(tmp_path: Path) -> None:
    from backend.db.repository import ActionRepository

    db = _db(tmp_path)
    DiagnoseAgent(db).run(_base_state())
    with db.connect() as conn:
        actions = ActionRepository.list_by_incident(conn, "inc-diag-001")
    assert any(a.agent_name == "diagnose" for a in actions)
