"""Tests for VerifyAgent (Unit 10)."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

import pytest

from backend.agents.verify_agent import VerifyAgent, VerificationSchema
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
                id="inc-ver-001",
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )
    return db


def _base_state() -> dict:
    return {
        "incident_id": "inc-ver-001",
        "scenario": "server_crash",
        "triggered_at": "2026-11-25T10:00:00Z",
        "replan_count": 0,
        "affected_services": ["resilience-web-server"],
        "recovery_strategy": "restart_container",
        "recovery_success": True,
    }


def test_verify_returns_verification_passed(tmp_path: Path) -> None:
    """In MOCK_MODE, verify agent should report verification_passed=True."""
    result = VerifyAgent(_db(tmp_path)).run(_base_state())
    assert result["verification_passed"] is True


def test_verify_replan_required_false_on_success(tmp_path: Path) -> None:
    result = VerifyAgent(_db(tmp_path)).run(_base_state())
    assert result["replan_required"] is False


def test_verify_post_metrics_contains_affected(tmp_path: Path) -> None:
    result = VerifyAgent(_db(tmp_path)).run(_base_state())
    metrics = result["post_recovery_metrics"]
    assert "resilience-web-server" in metrics


def test_verify_replan_count_unchanged_on_success(tmp_path: Path) -> None:
    """replan_count stays at 0 when verification passes."""
    result = VerifyAgent(_db(tmp_path)).run(_base_state())
    assert result["replan_count"] == 0


def test_verification_schema_rejects_invalid_combo() -> None:
    """VerificationSchema must raise if replan_required=True and verification_passed=True."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        VerificationSchema(
            verification_passed=True,
            replan_required=True,
            verdict_reasoning="This should fail validation",
        )


def test_verify_logs_action(tmp_path: Path) -> None:
    from backend.db.repository import ActionRepository

    db = _db(tmp_path)
    VerifyAgent(db).run(_base_state())
    with db.connect() as conn:
        actions = ActionRepository.list_by_incident(conn, "inc-ver-001")
    assert any(a.agent_name == "verify" for a in actions)
