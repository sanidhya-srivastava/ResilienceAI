"""Incident history and recovery metrics routes."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_db
from backend.api.schemas import (
    AgentActionResponse,
    IncidentDetailResponse,
    IncidentSummary,
    RecoveryMetricsResponse,
)
from backend.db.database import Database
from backend.db.repository import ActionRepository, IncidentRepository, MetricsRepository

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentSummary])
def list_incidents(db: Database = Depends(get_db)) -> list[IncidentSummary]:
    """List all recorded incidents ordered from newest to oldest."""
    with db.connect() as conn:
        incidents = IncidentRepository.list_all(conn)
    return [IncidentSummary(**asdict(inc)) for inc in incidents]


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(
    incident_id: str,
    db: Database = Depends(get_db),
) -> IncidentDetailResponse:
    """Return full incident details including agent actions and metrics."""
    with db.connect() as conn:
        incident = IncidentRepository.get_by_id(conn, incident_id)
        if incident is None:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        actions = ActionRepository.list_by_incident(conn, incident_id)
        metrics = MetricsRepository.get_by_incident(conn, incident_id)

    return IncidentDetailResponse(
        **asdict(incident),
        agent_actions=[AgentActionResponse(**asdict(a)) for a in actions],
        metrics=RecoveryMetricsResponse(**asdict(metrics)) if metrics else None,
    )


@router.get("/{incident_id}/metrics", response_model=RecoveryMetricsResponse)
def get_incident_metrics(
    incident_id: str,
    db: Database = Depends(get_db),
) -> RecoveryMetricsResponse:
    """Return quantitative recovery metrics for a single incident."""
    with db.connect() as conn:
        incident = IncidentRepository.get_by_id(conn, incident_id)
        if incident is None:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
        metrics = MetricsRepository.get_by_incident(conn, incident_id)
        if metrics is None:
            raise HTTPException(
                status_code=404,
                detail=f"Metrics not yet available for incident '{incident_id}'",
            )
    return RecoveryMetricsResponse(**asdict(metrics))
