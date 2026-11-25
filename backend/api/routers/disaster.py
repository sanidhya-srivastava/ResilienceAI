"""Disaster trigger and scenario listing routes."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_db
from backend.api.routers.websocket import manager
from backend.api.schemas import TriggerDisasterRequest, TriggerDisasterResponse
from backend.db.database import Database
from backend.db.models import Incident
from backend.db.repository import IncidentRepository, MetricsRepository
from backend.graph.runner import GraphRunner
from backend.simulator.scenarios import ScenarioRegistry
from backend.simulator.schemas import ScenarioInfo
from backend.simulator.utils import utcnow

router = APIRouter(prefix="/disaster", tags=["disaster"])

# Hold strong references to running background tasks so they are not GC'd.
_background_tasks: set[asyncio.Task[None]] = set()


async def _run_pipeline_bg(
    db: Database,
    incident_id: str,
    scenario: str,
    triggered_at: str,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Run the synchronous GraphRunner in a worker thread and broadcast updates."""

    def ws_callback(agent_name: str, partial: dict) -> None:
        payload = {
            "type": "agent_update",
            "incident_id": incident_id,
            "agent": agent_name,
            "state": partial,
            "timestamp": utcnow(),
        }
        loop.call_soon_threadsafe(
            lambda p=payload: loop.create_task(manager.broadcast(p))
        )

    try:
        final_state = await asyncio.to_thread(
            GraphRunner(db).run,
            incident_id,
            scenario,
            triggered_at,
            ws_callback,
        )
        with db.connect() as conn:
            metrics = MetricsRepository.get_by_incident(conn, incident_id)

        await manager.broadcast(
            {
                "type": "incident_complete",
                "incident_id": incident_id,
                "success": bool(final_state.get("verification_passed", False)),
                "metrics": asdict(metrics) if metrics else None,
            }
        )
    except Exception as exc:
        with db.connect() as conn:
            IncidentRepository.update_status(
                conn,
                incident_id=incident_id,
                status="failed",
                completed_at=utcnow(),
            )
        await manager.broadcast(
            {
                "type": "incident_complete",
                "incident_id": incident_id,
                "success": False,
                "metrics": None,
                "error": str(exc),
            }
        )


@router.get("/scenarios", response_model=list[ScenarioInfo])
def list_scenarios() -> list[ScenarioInfo]:
    """Return metadata for all registered disaster scenarios."""
    return ScenarioRegistry.list_all()


@router.post("/trigger", response_model=TriggerDisasterResponse)
async def trigger_disaster(
    body: TriggerDisasterRequest,
    db: Database = Depends(get_db),
) -> TriggerDisasterResponse:
    """Inject a disaster scenario and launch the recovery pipeline asynchronously."""
    try:
        scenario_impl = ScenarioRegistry.get(body.scenario)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    with db.connect() as conn:
        existing = IncidentRepository.list_all(conn)
        if any(inc.status == "in_progress" for inc in existing):
            raise HTTPException(
                status_code=409,
                detail="An incident recovery is already in progress.",
            )

        incident_id = str(uuid.uuid4())
        triggered_at = utcnow()
        IncidentRepository.create(
            conn,
            Incident(
                id=incident_id,
                scenario=body.scenario,
                triggered_at=triggered_at,
                status="in_progress",
            ),
        )

    scenario_impl.inject()

    loop = asyncio.get_running_loop()
    task = loop.create_task(
        _run_pipeline_bg(db, incident_id, body.scenario, triggered_at, loop)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return TriggerDisasterResponse(
        incident_id=incident_id,
        status="triggered",
        triggered_at=triggered_at,
    )
