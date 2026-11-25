"""Direct unit & integration tests for FastAPI routes and WebSocket manager.

Routes are invoked directly (avoiding TestClient on Windows/anyio).
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

from fastapi import HTTPException
import pytest

from backend.api.routers.disaster import (
    _background_tasks,
    list_scenarios,
    trigger_disaster,
)
from backend.api.routers.incidents import (
    get_incident,
    get_incident_metrics,
    list_incidents,
)
from backend.api.routers.websocket import manager
from backend.api.schemas import TriggerDisasterRequest
from backend.db.database import Database
from backend.db.models import Incident
from backend.db.repository import IncidentRepository


def _make_db(tmp_path: Path) -> Database:
    db = Database(str(tmp_path / "api_test.db"))
    db.init_db()
    return db


class _FakeWebSocket:
    """Minimal in-memory WebSocket double for testing ConnectionManager."""

    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


def test_list_scenarios_returns_server_crash() -> None:
    scenarios = list_scenarios()
    names = [s.name for s in scenarios]
    assert "server_crash" in names


def test_trigger_unknown_scenario_raises_422(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            trigger_disaster(TriggerDisasterRequest(scenario="does_not_exist"), db=db)
        )
    assert exc_info.value.status_code == 422


def test_trigger_while_in_progress_raises_409(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    with db.connect() as conn:
        IncidentRepository.create(
            conn,
            Incident(
                id="inc-active-001",
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            trigger_disaster(TriggerDisasterRequest(scenario="server_crash"), db=db)
        )
    assert exc_info.value.status_code == 409


def test_trigger_and_read_incident_flow_with_ws_broadcast(tmp_path: Path) -> None:
    """Triggering a disaster completes in background, logs actions/metrics, and broadcasts WS events."""
    db = _make_db(tmp_path)
    fake_ws = _FakeWebSocket()

    async def _execute() -> str:
        await manager.connect(fake_ws)  # type: ignore[arg-type]
        try:
            resp = await trigger_disaster(
                TriggerDisasterRequest(scenario="server_crash"), db=db
            )
            assert resp.status == "triggered"
            # Wait for spawned background pipeline task to finish
            if _background_tasks:
                await asyncio.gather(*list(_background_tasks))
            # Allow any queued call_soon_threadsafe broadcast tasks to drain
            await asyncio.sleep(0.05)
            return resp.incident_id
        finally:
            manager.disconnect(fake_ws)  # type: ignore[arg-type]

    incident_id = asyncio.run(_execute())

    # Verify REST query functions return full incident, 5 actions, and metrics
    incidents = list_incidents(db=db)
    assert len(incidents) == 1
    assert incidents[0].id == incident_id
    assert incidents[0].status == "recovered"

    detail = get_incident(incident_id, db=db)
    assert [a.agent_name for a in detail.agent_actions] == [
        "monitor",
        "diagnose",
        "plan",
        "recover",
        "verify",
    ]
    assert detail.metrics is not None
    assert detail.metrics.success is True

    metrics = get_incident_metrics(incident_id, db=db)
    assert metrics.recovery_strategy == "restart_container"
    assert metrics.mttr_seconds is not None and metrics.mttr_seconds > 0

    # Verify WebSocket broadcasts: 5 agent_update + 1 incident_complete
    update_events = [m for m in fake_ws.sent if m["type"] == "agent_update"]
    complete_events = [m for m in fake_ws.sent if m["type"] == "incident_complete"]
    assert [e["agent"] for e in update_events] == [
        "monitor",
        "diagnose",
        "plan",
        "recover",
        "verify",
    ]
    assert len(complete_events) == 1
    assert complete_events[0]["success"] is True


def test_get_missing_incident_raises_404(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        get_incident("missing-id", db=db)
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info2:
        get_incident_metrics("missing-id", db=db)
    assert exc_info2.value.status_code == 404
