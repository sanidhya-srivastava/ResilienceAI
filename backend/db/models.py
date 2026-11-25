from dataclasses import dataclass


@dataclass(frozen=True)
class Incident:
    """Represents a simulated disaster incident record."""

    id: str
    scenario: str
    triggered_at: str
    status: str  # "in_progress" | "recovered" | "failed"
    completed_at: str | None = None
    total_duration_seconds: float | None = None


@dataclass(frozen=True)
class AgentAction:
    """Represents a single agent execution step logged for an incident."""

    incident_id: str
    agent_name: str  # "monitor" | "diagnose" | "plan" | "recover" | "verify"
    action_type: str
    success: bool
    timestamp: str
    id: int | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class RecoveryMetrics:
    """Represents quantitative recovery performance metrics for an incident."""

    incident_id: str
    success: bool
    mttr_seconds: float | None = None
    detection_time_seconds: float | None = None
    diagnosis_time_seconds: float | None = None
    planning_time_seconds: float | None = None
    recovery_time_seconds: float | None = None
    verification_time_seconds: float | None = None
    replan_count: int = 0
    recovery_strategy: str | None = None
