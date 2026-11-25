"""RecoveryState — the shared typed state passed through the LangGraph pipeline."""
from __future__ import annotations

from typing import NotRequired, TypedDict


class RecoveryState(TypedDict):
    # ── Required at graph start ────────────────────────────────────────────────
    incident_id: str
    scenario: str
    triggered_at: str
    replan_count: int  # starts at 0; incremented by verify on each replan

    # ── Set by Monitor Agent ───────────────────────────────────────────────────
    affected_services: NotRequired[list[str]]
    health_metrics: NotRequired[dict]       # {service: {status, healthy, ...}}
    anomaly_detected: NotRequired[bool]
    anomaly_description: NotRequired[str]

    # ── Set by Diagnose Agent ──────────────────────────────────────────────────
    root_cause: NotRequired[str]            # enum — see DiagnosisSchema
    severity: NotRequired[str]              # "critical" | "high" | "medium" | "low"
    diagnosis_confidence: NotRequired[float]

    # ── Set by Plan Agent ──────────────────────────────────────────────────────
    recovery_strategy: NotRequired[str]     # enum — see STRATEGY_CATALOG
    recovery_steps: NotRequired[list[str]]
    estimated_rto_seconds: NotRequired[int]

    # ── Set by Recover Agent ───────────────────────────────────────────────────
    actions_taken: NotRequired[list[dict]]
    recovery_attempted: NotRequired[bool]
    recovery_success: NotRequired[bool]

    # ── Set by Verify Agent ────────────────────────────────────────────────────
    verification_passed: NotRequired[bool]
    post_recovery_metrics: NotRequired[dict]
    replan_required: NotRequired[bool]      # True → graph loops back to Plan
    verdict_reasoning: NotRequired[str]

    # ── Set by GraphRunner on completion ──────────────────────────────────────
    completed_at: NotRequired[str | None]
    total_duration_seconds: NotRequired[float | None]
