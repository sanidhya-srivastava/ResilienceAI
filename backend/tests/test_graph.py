"""Tests for the LangGraph RecoveryGraph structure and mock execution."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

import pytest

from backend.graph.state import RecoveryState


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_stub_agent(name: str, output: dict):
    """Return a minimal agent stub that returns a fixed output dict."""
    from backend.graph.base_agent import BaseAgent  # noqa: PLC0415
    from backend.db.database import Database  # noqa: PLC0415

    class StubAgent(BaseAgent):
        def run(self, state: RecoveryState) -> dict:  # type: ignore[override]
            return output

    stub = object.__new__(StubAgent)
    stub.name = name
    stub.db = None  # DB not needed for structure tests
    return stub


# ── Graph structure tests ──────────────────────────────────────────────────────

def test_graph_compiles_without_error() -> None:
    """build_recovery_graph() should compile successfully with stub agents."""
    from backend.graph.graph import build_recovery_graph  # noqa: PLC0415

    agents = {
        name: _make_stub_agent(name, {})
        for name in ("monitor", "diagnose", "plan", "recover", "verify")
    }
    compiled = build_recovery_graph(agents)
    assert compiled is not None


def test_graph_has_all_five_nodes() -> None:
    """The compiled graph must contain exactly the five agent nodes."""
    from backend.graph.graph import build_recovery_graph  # noqa: PLC0415

    agents = {
        name: _make_stub_agent(name, {})
        for name in ("monitor", "diagnose", "plan", "recover", "verify")
    }
    compiled = build_recovery_graph(agents)
    node_ids = set(compiled.get_graph().nodes.keys())
    for expected in ("monitor", "diagnose", "plan", "recover", "verify"):
        assert expected in node_ids, f"Node '{expected}' missing from graph"


def test_mock_runner_completes_end_to_end(tmp_path: Path) -> None:
    """GraphRunner in MOCK_MODE returns a complete RecoveryState without errors."""
    from backend.db.database import Database  # noqa: PLC0415
    from backend.graph.runner import GraphRunner  # noqa: PLC0415
    from backend.db.models import Incident  # noqa: PLC0415
    from backend.db.repository import IncidentRepository  # noqa: PLC0415

    db = Database(str(tmp_path / "run_test.db"))
    db.init_db()

    # Pre-create the incident so runner can update its status
    with db.connect() as conn:
        IncidentRepository.create(conn, Incident(
            id="inc-graph-001",
            scenario="server_crash",
            triggered_at="2026-11-25T10:00:00Z",
            status="in_progress",
        ))

    runner = GraphRunner(db)
    state = runner.run(
        incident_id="inc-graph-001",
        scenario="server_crash",
        triggered_at="2026-11-25T10:00:00Z",
    )

    assert state["incident_id"] == "inc-graph-001"
    assert state["anomaly_detected"] is True
    assert state["root_cause"] == "container_crash"
    assert state["recovery_strategy"] == "restart_container"
    assert state["recovery_success"] is True
    assert state["verification_passed"] is True
    assert state.get("completed_at") is not None


def test_mock_runner_calls_ws_callback_for_each_agent(tmp_path: Path) -> None:
    """ws_callback is invoked once per agent in MOCK_MODE."""
    from backend.db.database import Database  # noqa: PLC0415
    from backend.graph.runner import GraphRunner  # noqa: PLC0415
    from backend.db.models import Incident  # noqa: PLC0415
    from backend.db.repository import IncidentRepository  # noqa: PLC0415

    db = Database(str(tmp_path / "cb_test.db"))
    db.init_db()
    with db.connect() as conn:
        IncidentRepository.create(conn, Incident(
            id="inc-graph-002",
            scenario="server_crash",
            triggered_at="2026-11-25T10:00:00Z",
            status="in_progress",
        ))

    received: list[str] = []

    def ws_callback(agent_name: str, partial: dict) -> None:
        received.append(agent_name)

    GraphRunner(db).run(
        incident_id="inc-graph-002",
        scenario="server_crash",
        triggered_at="2026-11-25T10:00:00Z",
        ws_callback=ws_callback,
    )

    assert received == ["monitor", "diagnose", "plan", "recover", "verify"]


def test_should_replan_guard_caps_at_max_replans() -> None:
    """_should_replan returns END when replan_count >= MAX_REPLANS."""
    from langgraph.graph import END  # noqa: PLC0415
    from backend.graph.graph import _should_replan, MAX_REPLANS  # noqa: PLC0415

    # Below limit — should replan
    state_below: RecoveryState = {
        "incident_id": "x", "scenario": "s", "triggered_at": "t",
        "replan_count": MAX_REPLANS - 1,
        "replan_required": True,
    }
    assert _should_replan(state_below) == "plan"

    # At limit — should stop
    state_at: RecoveryState = {
        "incident_id": "x", "scenario": "s", "triggered_at": "t",
        "replan_count": MAX_REPLANS,
        "replan_required": True,
    }
    assert _should_replan(state_at) == END

    # No replan needed — should stop
    state_ok: RecoveryState = {
        "incident_id": "x", "scenario": "s", "triggered_at": "t",
        "replan_count": 0,
        "replan_required": False,
    }
    assert _should_replan(state_ok) == END
