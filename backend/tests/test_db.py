from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3

import pytest

from backend.db.database import Database
from backend.db.models import AgentAction, Incident, RecoveryMetrics
from backend.db.repository import (
    ActionRepository,
    IncidentRepository,
    MetricsRepository,
)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Create an initialized temporary SQLite database for testing."""
    database = Database(str(tmp_path / "test_incidents.db"))
    database.init_db()
    return database


def test_happy_path_incident_actions_and_metrics(db: Database) -> None:
    """Create an incident, log 5 agent actions, write metrics, and read all back."""
    incident = Incident(
        id="inc-001",
        scenario="server_crash",
        triggered_at="2026-11-25T10:00:00Z",
        status="in_progress",
    )
    agents = ["monitor", "diagnose", "plan", "recover", "verify"]

    with db.connect() as conn:
        IncidentRepository.create(conn, incident)
        for name in agents:
            ActionRepository.create(
                conn,
                AgentAction(
                    incident_id="inc-001",
                    agent_name=name,
                    action_type="execute",
                    input_summary="input",
                    output_summary="output",
                    success=True,
                    duration_ms=120,
                    timestamp="2026-11-25T10:00:01Z",
                ),
            )
        MetricsRepository.upsert(
            conn,
            RecoveryMetrics(
                incident_id="inc-001",
                mttr_seconds=4.5,
                detection_time_seconds=0.5,
                diagnosis_time_seconds=1.0,
                planning_time_seconds=1.0,
                recovery_time_seconds=1.5,
                verification_time_seconds=0.5,
                replan_count=0,
                recovery_strategy="restart_container",
                success=True,
            ),
        )
        IncidentRepository.update_status(
            conn,
            "inc-001",
            status="recovered",
            completed_at="2026-11-25T10:00:05Z",
            total_duration_seconds=4.5,
        )

        fetched_incident = IncidentRepository.get_by_id(conn, "inc-001")
        fetched_actions = ActionRepository.list_by_incident(conn, "inc-001")
        fetched_metrics = MetricsRepository.get_by_incident(conn, "inc-001")

    assert fetched_incident is not None
    assert fetched_incident.status == "recovered"
    assert [a.agent_name for a in fetched_actions] == agents
    assert fetched_metrics is not None
    assert fetched_metrics.mttr_seconds == 4.5
    assert fetched_metrics.success is True


def test_get_nonexistent_incident_returns_none(db: Database) -> None:
    """Querying a missing incident_id returns None instead of raising."""
    with db.connect() as conn:
        assert IncidentRepository.get_by_id(conn, "missing-id") is None
        assert MetricsRepository.get_by_incident(conn, "missing-id") is None


def test_action_for_nonexistent_incident_raises_integrity_error(db: Database) -> None:
    """Foreign key enforcement rejects actions for an unknown incident_id."""
    with db.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            ActionRepository.create(
                conn,
                AgentAction(
                    incident_id="does-not-exist",
                    agent_name="monitor",
                    action_type="check",
                    success=True,
                    timestamp="2026-11-25T10:00:00Z",
                ),
            )


def test_concurrent_action_writes(db: Database) -> None:
    """Two simultaneous action inserts for the same incident succeed in WAL mode."""
    with db.connect() as conn:
        IncidentRepository.create(
            conn,
            Incident(
                id="inc-wal",
                scenario="server_crash",
                triggered_at="2026-11-25T10:00:00Z",
                status="in_progress",
            ),
        )

    def insert_action(agent_name: str) -> None:
        with db.connect() as conn:
            ActionRepository.create(
                conn,
                AgentAction(
                    incident_id="inc-wal",
                    agent_name=agent_name,
                    action_type="concurrent_check",
                    success=True,
                    timestamp="2026-11-25T10:00:01Z",
                ),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(insert_action, name) for name in ("monitor", "diagnose")]
        for f in futures:
            f.result()

    with db.connect() as conn:
        actions = ActionRepository.list_by_incident(conn, "inc-wal")
    assert len(actions) == 2
