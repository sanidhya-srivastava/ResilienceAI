"""Mock responses for all five agents used when MOCK_MODE=true.

Each entry is a plain dict. Agents validate it against their Pydantic schema
via  schema.model_validate(MOCK_LLM_RESPONSES[agent_name]).
"""
from __future__ import annotations

MOCK_LLM_RESPONSES: dict[str, dict] = {
    "monitor": {
        "anomaly_description": "web-server container stopped unexpectedly — /health unreachable",
        "urgency": "critical",
    },
    "diagnose": {
        "root_cause": "container_crash",
        "severity": "critical",
        "diagnosis_confidence": 0.95,
        "reasoning": "web-server exited with status 137 (OOM kill or explicit stop)",
    },
    "plan": {
        "selected_strategy": "restart_container",
        "rationale": "Container crash detected; a simple restart is fastest recovery path",
        "confidence": 0.92,
    },
    # Recover agent is deterministic (tool-based); no LLM call.
    "recover": {},
    "verify": {
        "verification_passed": True,
        "replan_required": False,
        "verdict_reasoning": "All services healthy after container restart",
    },
}

# Pre-built full RecoveryState updates returned by each mock agent's run().
# Used by GraphRunner in mock mode to bypass the real agent implementations.
MOCK_AGENT_OUTPUTS: dict[str, dict] = {
    "monitor": {
        "affected_services": ["resilience-web-server"],
        "health_metrics": {
            "resilience-web-server": {"healthy": False, "status": "exited"},
            "resilience-database": {"healthy": True, "status": "running"},
            "resilience-backup-store": {"healthy": True, "status": "running"},
        },
        "anomaly_detected": True,
        "anomaly_description": "web-server container stopped unexpectedly",
    },
    "diagnose": {
        "root_cause": "container_crash",
        "severity": "critical",
        "diagnosis_confidence": 0.95,
    },
    "plan": {
        "recovery_strategy": "restart_container",
        "recovery_steps": [
            "Stop the resilience-web-server container",
            "Start the resilience-web-server container",
            "Wait for /health endpoint to return 200",
        ],
        "estimated_rto_seconds": 30,
    },
    "recover": {
        "actions_taken": [
            {
                "action": "restart:resilience-web-server",
                "timestamp": "2026-11-25T10:00:03Z",
                "success": True,
                "detail": "Container restarted successfully",
            }
        ],
        "recovery_attempted": True,
        "recovery_success": True,
    },
    "verify": {
        "verification_passed": True,
        "post_recovery_metrics": {
            "resilience-web-server": {"healthy": True, "status": "running"},
        },
        "replan_required": False,
        "verdict_reasoning": "All services healthy after restart",
    },
}
