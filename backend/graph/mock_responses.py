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

# Default single-pass mock outputs (used by server_crash and as fallback).
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


# Per-scenario agent step sequences for MOCK_MODE=true demos.
# Tricky scenarios like `corrupted_config` exercise the Verify -> Plan replan loop.
MOCK_SCENARIO_SEQUENCES: dict[str, list[tuple[str, dict]]] = {
    "server_crash": list(MOCK_AGENT_OUTPUTS.items()),
    "database_connection_lost": [
        (
            "monitor",
            {
                "affected_services": ["resilience-database"],
                "health_metrics": {
                    "resilience-web-server": {"healthy": True, "status": "running"},
                    "resilience-database": {"healthy": False, "status": "exited"},
                    "resilience-backup-store": {"healthy": True, "status": "running"},
                },
                "anomaly_detected": True,
                "anomaly_description": "PostgreSQL pg_isready probe failed — DB unreachable",
            },
        ),
        (
            "diagnose",
            {
                "root_cause": "database_connection_lost",
                "severity": "critical",
                "diagnosis_confidence": 0.96,
            },
        ),
        (
            "plan",
            {
                "recovery_strategy": "restart_container",
                "recovery_steps": [
                    "Restart the resilience-database container",
                    "Re-run pg_isready connection probe",
                    "Verify downstream services can reach PostgreSQL",
                ],
                "estimated_rto_seconds": 45,
            },
        ),
        (
            "recover",
            {
                "actions_taken": [
                    {
                        "action": "restart:resilience-database",
                        "timestamp": "2026-11-26T10:00:03Z",
                        "success": True,
                        "detail": "PostgreSQL container restarted and accepting connections",
                    }
                ],
                "recovery_attempted": True,
                "recovery_success": True,
            },
        ),
        (
            "verify",
            {
                "verification_passed": True,
                "post_recovery_metrics": {
                    "resilience-database": {"healthy": True, "status": "running"},
                },
                "replan_required": False,
                "verdict_reasoning": "PostgreSQL accepting connections on port 5432",
            },
        ),
    ],
    "oom_kill": [
        (
            "monitor",
            {
                "affected_services": ["resilience-web-server"],
                "health_metrics": {
                    "resilience-web-server": {"healthy": False, "status": "exited (137)"},
                    "resilience-database": {"healthy": True, "status": "running"},
                    "resilience-backup-store": {"healthy": True, "status": "running"},
                },
                "anomaly_detected": True,
                "anomaly_description": "web-server killed abruptly with SIGKILL (exit 137)",
            },
        ),
        (
            "diagnose",
            {
                "root_cause": "oom_kill",
                "severity": "high",
                "diagnosis_confidence": 0.91,
            },
        ),
        (
            "plan",
            {
                "recovery_strategy": "restart_container",
                "recovery_steps": [
                    "Restart the OOM-killed container",
                    "Verify /health endpoint stabilizes",
                ],
                "estimated_rto_seconds": 30,
            },
        ),
        (
            "recover",
            {
                "actions_taken": [
                    {
                        "action": "restart:resilience-web-server",
                        "timestamp": "2026-11-26T10:00:03Z",
                        "success": True,
                        "detail": "Container restarted cleanly after SIGKILL",
                    }
                ],
                "recovery_attempted": True,
                "recovery_success": True,
            },
        ),
        (
            "verify",
            {
                "verification_passed": True,
                "post_recovery_metrics": {
                    "resilience-web-server": {"healthy": True, "status": "running"},
                },
                "replan_required": False,
                "verdict_reasoning": "web-server recovered and serving HTTP 200 on /health",
            },
        ),
    ],
    "disk_full": [
        (
            "monitor",
            {
                "affected_services": ["resilience-backup-store"],
                "health_metrics": {
                    "resilience-web-server": {"healthy": True, "status": "running"},
                    "resilience-database": {"healthy": True, "status": "running"},
                    "resilience-backup-store": {"healthy": False, "status": "disk_full"},
                },
                "anomaly_detected": True,
                "anomaly_description": "backup-store container running, but scratch storage exhausted",
            },
        ),
        (
            "diagnose",
            {
                "root_cause": "disk_full",
                "severity": "high",
                "diagnosis_confidence": 0.94,
            },
        ),
        (
            "plan",
            {
                "recovery_strategy": "cleanup_disk",
                "recovery_steps": [
                    "Identify large temporary fill files on resilience-backup-store",
                    "Prune /tmp/disk_fill.bin and stale logs",
                    "Verify disk headroom restored",
                ],
                "estimated_rto_seconds": 25,
            },
        ),
        (
            "recover",
            {
                "actions_taken": [
                    {
                        "action": "cleanup_disk:resilience-backup-store",
                        "timestamp": "2026-11-26T10:00:03Z",
                        "success": True,
                        "detail": "Pruned temporary fill files on resilience-backup-store",
                    }
                ],
                "recovery_attempted": True,
                "recovery_success": True,
            },
        ),
        (
            "verify",
            {
                "verification_passed": True,
                "post_recovery_metrics": {
                    "resilience-backup-store": {"healthy": True, "status": "running"},
                },
                "replan_required": False,
                "verdict_reasoning": "Disk fill artifact removed; backup-store healthy",
            },
        ),
    ],
    "corrupted_config": [
        (
            "monitor",
            {
                "affected_services": ["resilience-web-server"],
                "health_metrics": {
                    "resilience-web-server": {"healthy": False, "status": "unhealthy (HTTP 502)"},
                    "resilience-database": {"healthy": True, "status": "running"},
                    "resilience-backup-store": {"healthy": True, "status": "running"},
                },
                "anomaly_detected": True,
                "anomaly_description": "web-server failing /health after nginx configuration error",
            },
        ),
        (
            "diagnose",
            {
                "root_cause": "config_corruption",
                "severity": "critical",
                "diagnosis_confidence": 0.89,
            },
        ),
        (
            "plan",
            {
                "recovery_strategy": "restart_container",
                "recovery_steps": [
                    "Attempt container restart to reload configuration",
                    "Verify HTTP /health endpoint returns 200",
                ],
                "estimated_rto_seconds": 20,
            },
        ),
        (
            "recover",
            {
                "actions_taken": [
                    {
                        "action": "restart:resilience-web-server",
                        "timestamp": "2026-11-26T10:00:03Z",
                        "success": True,
                        "detail": "Container restarted, but invalid nginx directive persisted",
                    }
                ],
                "recovery_attempted": True,
                "recovery_success": True,
            },
        ),
        (
            "verify",
            {
                "verification_passed": False,
                "post_recovery_metrics": {
                    "resilience-web-server": {"healthy": False, "status": "unreachable"},
                },
                "replan_required": True,
                "replan_count": 1,
                "verdict_reasoning": "Simple restart did not fix broken nginx config; replanning with backup restore",
            },
        ),
        (
            "plan",
            {
                "recovery_strategy": "restore_from_backup",
                "recovery_steps": [
                    "Restore clean nginx configuration from backup",
                    "Restart resilience-web-server container",
                    "Verify HTTP /health endpoint returns 200",
                ],
                "estimated_rto_seconds": 60,
            },
        ),
        (
            "recover",
            {
                "actions_taken": [
                    {
                        "action": "restore_backup:resilience-web-server",
                        "timestamp": "2026-11-26T10:00:06Z",
                        "success": True,
                        "detail": "Restored clean nginx config from backup-store",
                    },
                    {
                        "action": "restart:resilience-web-server",
                        "timestamp": "2026-11-26T10:00:07Z",
                        "success": True,
                        "detail": "Container restarted cleanly with valid config",
                    },
                ],
                "recovery_attempted": True,
                "recovery_success": True,
            },
        ),
        (
            "verify",
            {
                "verification_passed": True,
                "post_recovery_metrics": {
                    "resilience-web-server": {"healthy": True, "status": "running"},
                },
                "replan_required": False,
                "replan_count": 1,
                "verdict_reasoning": "Restored configuration from backup resolved HTTP /health failures",
            },
        ),
    ],
    "cascading_failure": [
        (
            "monitor",
            {
                "affected_services": ["resilience-database", "resilience-web-server"],
                "health_metrics": {
                    "resilience-web-server": {"healthy": False, "status": "exited"},
                    "resilience-database": {"healthy": False, "status": "exited"},
                    "resilience-backup-store": {"healthy": True, "status": "running"},
                },
                "anomaly_detected": True,
                "anomaly_description": "Multi-service outage: PostgreSQL and web-server both offline",
            },
        ),
        (
            "diagnose",
            {
                "root_cause": "cascading_failure",
                "severity": "critical",
                "diagnosis_confidence": 0.93,
            },
        ),
        (
            "plan",
            {
                "recovery_strategy": "ordered_recovery",
                "recovery_steps": [
                    "Start resilience-database first and wait for pg_isready",
                    "Restart dependent resilience-web-server container",
                    "Verify end-to-end health across all services",
                ],
                "estimated_rto_seconds": 45,
            },
        ),
        (
            "recover",
            {
                "actions_taken": [
                    {
                        "action": "restart:resilience-database",
                        "timestamp": "2026-11-26T10:00:03Z",
                        "success": True,
                        "detail": "Database brought online first",
                    },
                    {
                        "action": "restart:resilience-web-server",
                        "timestamp": "2026-11-26T10:00:04Z",
                        "success": True,
                        "detail": "Dependent web-server restarted cleanly",
                    },
                ],
                "recovery_attempted": True,
                "recovery_success": True,
            },
        ),
        (
            "verify",
            {
                "verification_passed": True,
                "post_recovery_metrics": {
                    "resilience-database": {"healthy": True, "status": "running"},
                    "resilience-web-server": {"healthy": True, "status": "running"},
                },
                "replan_required": False,
                "verdict_reasoning": "Both database and web-server verified healthy in dependency order",
            },
        ),
    ],
}
