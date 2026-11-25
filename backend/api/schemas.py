"""Pydantic request and response schemas for the FastAPI layer."""
from __future__ import annotations

from pydantic import BaseModel


class TriggerDisasterRequest(BaseModel):
    scenario: str


class TriggerDisasterResponse(BaseModel):
    incident_id: str
    status: str
    triggered_at: str


class IncidentSummary(BaseModel):
    id: str
    scenario: str
    triggered_at: str
    status: str
    completed_at: str | None = None
    total_duration_seconds: float | None = None


class AgentActionResponse(BaseModel):
    id: int | None = None
    incident_id: str
    agent_name: str
    action_type: str
    input_summary: str | None = None
    output_summary: str | None = None
    success: bool
    duration_ms: int | None = None
    timestamp: str


class RecoveryMetricsResponse(BaseModel):
    incident_id: str
    mttr_seconds: float | None = None
    detection_time_seconds: float | None = None
    diagnosis_time_seconds: float | None = None
    planning_time_seconds: float | None = None
    recovery_time_seconds: float | None = None
    verification_time_seconds: float | None = None
    replan_count: int = 0
    recovery_strategy: str | None = None
    success: bool


class IncidentDetailResponse(IncidentSummary):
    agent_actions: list[AgentActionResponse]
    metrics: RecoveryMetricsResponse | None = None
