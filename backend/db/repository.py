import sqlite3

from backend.db.models import AgentAction, Incident, RecoveryMetrics


class IncidentRepository:
    """CRUD operations for the incidents table."""

    @staticmethod
    def create(conn: sqlite3.Connection, incident: Incident) -> Incident:
        conn.execute(
            """
            INSERT INTO incidents (id, scenario, triggered_at, completed_at, status, total_duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                incident.id,
                incident.scenario,
                incident.triggered_at,
                incident.completed_at,
                incident.status,
                incident.total_duration_seconds,
            ),
        )
        conn.commit()
        return incident

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, incident_id: str) -> Incident | None:
        row = conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
        if row is None:
            return None
        return Incident(
            id=row["id"],
            scenario=row["scenario"],
            triggered_at=row["triggered_at"],
            completed_at=row["completed_at"],
            status=row["status"],
            total_duration_seconds=row["total_duration_seconds"],
        )

    @staticmethod
    def list_all(conn: sqlite3.Connection) -> list[Incident]:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY triggered_at DESC"
        ).fetchall()
        return [
            Incident(
                id=row["id"],
                scenario=row["scenario"],
                triggered_at=row["triggered_at"],
                completed_at=row["completed_at"],
                status=row["status"],
                total_duration_seconds=row["total_duration_seconds"],
            )
            for row in rows
        ]

    @staticmethod
    def update_status(
        conn: sqlite3.Connection,
        incident_id: str,
        status: str,
        completed_at: str | None = None,
        total_duration_seconds: float | None = None,
    ) -> None:
        conn.execute(
            """
            UPDATE incidents
            SET status = ?, completed_at = ?, total_duration_seconds = ?
            WHERE id = ?
            """,
            (status, completed_at, total_duration_seconds, incident_id),
        )
        conn.commit()


class ActionRepository:
    """Persistence operations for the agent_actions table."""

    @staticmethod
    def create(conn: sqlite3.Connection, action: AgentAction) -> AgentAction:
        cursor = conn.execute(
            """
            INSERT INTO agent_actions (
                incident_id, agent_name, action_type, input_summary,
                output_summary, success, duration_ms, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action.incident_id,
                action.agent_name,
                action.action_type,
                action.input_summary,
                action.output_summary,
                1 if action.success else 0,
                action.duration_ms,
                action.timestamp,
            ),
        )
        conn.commit()
        return AgentAction(
            id=cursor.lastrowid,
            incident_id=action.incident_id,
            agent_name=action.agent_name,
            action_type=action.action_type,
            input_summary=action.input_summary,
            output_summary=action.output_summary,
            success=action.success,
            duration_ms=action.duration_ms,
            timestamp=action.timestamp,
        )

    @staticmethod
    def list_by_incident(
        conn: sqlite3.Connection, incident_id: str
    ) -> list[AgentAction]:
        rows = conn.execute(
            "SELECT * FROM agent_actions WHERE incident_id = ? ORDER BY id ASC",
            (incident_id,),
        ).fetchall()
        return [
            AgentAction(
                id=row["id"],
                incident_id=row["incident_id"],
                agent_name=row["agent_name"],
                action_type=row["action_type"],
                input_summary=row["input_summary"],
                output_summary=row["output_summary"],
                success=bool(row["success"]),
                duration_ms=row["duration_ms"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]


class MetricsRepository:
    """Persistence operations for the recovery_metrics table."""

    @staticmethod
    def upsert(conn: sqlite3.Connection, metrics: RecoveryMetrics) -> RecoveryMetrics:
        conn.execute(
            """
            INSERT INTO recovery_metrics (
                incident_id, mttr_seconds, detection_time_seconds,
                diagnosis_time_seconds, planning_time_seconds,
                recovery_time_seconds, verification_time_seconds,
                replan_count, recovery_strategy, success
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(incident_id) DO UPDATE SET
                mttr_seconds = excluded.mttr_seconds,
                detection_time_seconds = excluded.detection_time_seconds,
                diagnosis_time_seconds = excluded.diagnosis_time_seconds,
                planning_time_seconds = excluded.planning_time_seconds,
                recovery_time_seconds = excluded.recovery_time_seconds,
                verification_time_seconds = excluded.verification_time_seconds,
                replan_count = excluded.replan_count,
                recovery_strategy = excluded.recovery_strategy,
                success = excluded.success
            """,
            (
                metrics.incident_id,
                metrics.mttr_seconds,
                metrics.detection_time_seconds,
                metrics.diagnosis_time_seconds,
                metrics.planning_time_seconds,
                metrics.recovery_time_seconds,
                metrics.verification_time_seconds,
                metrics.replan_count,
                metrics.recovery_strategy,
                1 if metrics.success else 0,
            ),
        )
        conn.commit()
        return metrics

    @staticmethod
    def get_by_incident(
        conn: sqlite3.Connection, incident_id: str
    ) -> RecoveryMetrics | None:
        row = conn.execute(
            "SELECT * FROM recovery_metrics WHERE incident_id = ?", (incident_id,)
        ).fetchone()
        if row is None:
            return None
        return RecoveryMetrics(
            incident_id=row["incident_id"],
            mttr_seconds=row["mttr_seconds"],
            detection_time_seconds=row["detection_time_seconds"],
            diagnosis_time_seconds=row["diagnosis_time_seconds"],
            planning_time_seconds=row["planning_time_seconds"],
            recovery_time_seconds=row["recovery_time_seconds"],
            verification_time_seconds=row["verification_time_seconds"],
            replan_count=row["replan_count"],
            recovery_strategy=row["recovery_strategy"],
            success=bool(row["success"]),
        )
