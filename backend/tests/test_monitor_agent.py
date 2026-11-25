"""Tests for MonitorAgent (Unit 6)."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

import pytest

from backend.agents.monitor_agent import MonitorAgent
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
                id="inc-mon-001",
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )
    return db


def test_monitor_returns_affected_services(tmp_path: Path) -> None:
    """In MOCK_MODE, web-server is unhealthy → appears in affected_services."""
    agent = MonitorAgent(_db(tmp_path))
    state = {"incident_id": "inc-mon-001", "scenario": "server_crash",
              "triggered_at": "2026-11-25T10:00:00Z", "replan_count": 0}
    result = agent.run(state)

    assert "affected_services" in result
    assert "resilience-web-server" in result["affected_services"]


def test_monitor_anomaly_detected_true(tmp_path: Path) -> None:
    """anomaly_detected is True when at least one service is unhealthy."""
    agent = MonitorAgent(_db(tmp_path))
    state = {"incident_id": "inc-mon-001", "scenario": "server_crash",
              "triggered_at": "2026-11-25T10:00:00Z", "replan_count": 0}
    result = agent.run(state)

    assert result["anomaly_detected"] is True


def test_monitor_health_metrics_has_all_services(tmp_path: Path) -> None:
    """health_metrics contains an entry for each service."""
    agent = MonitorAgent(_db(tmp_path))
    state = {"incident_id": "inc-mon-001", "scenario": "server_crash",
              "triggered_at": "2026-11-25T10:00:00Z", "replan_count": 0}
    result = agent.run(state)

    metrics = result["health_metrics"]
    assert "resilience-web-server" in metrics
    assert "resilience-database" in metrics
    assert "resilience-backup-store" in metrics


def test_monitor_anomaly_description_nonempty(tmp_path: Path) -> None:
    """When anomaly detected, anomaly_description is a non-empty string."""
    agent = MonitorAgent(_db(tmp_path))
    state = {"incident_id": "inc-mon-001", "scenario": "server_crash",
              "triggered_at": "2026-11-25T10:00:00Z", "replan_count": 0}
    result = agent.run(state)

    assert isinstance(result["anomaly_description"], str)
    assert len(result["anomaly_description"]) > 0


def test_monitor_logs_action_to_db(tmp_path: Path) -> None:
    """MonitorAgent persists an action record to the database."""
    from backend.db.repository import ActionRepository

    db = _db(tmp_path)
    agent = MonitorAgent(db)
    state = {"incident_id": "inc-mon-001", "scenario": "server_crash",
              "triggered_at": "2026-11-25T10:00:00Z", "replan_count": 0}
    agent.run(state)

    with db.connect() as conn:
        actions = ActionRepository.list_by_incident(conn, "inc-mon-001")
    assert any(a.agent_name == "monitor" for a in actions)
