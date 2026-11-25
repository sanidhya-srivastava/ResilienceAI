"""Recovery strategy catalog — maps root causes to ordered strategy lists.

Strategies are tried in order; if the Verify Agent requires a replan, the
Plan Agent excludes the previously tried strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RecoveryStrategy:
    name: str                       # unique key used by STRATEGY_HANDLERS in RecoverAgent
    steps: list[str] = field(default_factory=list)
    estimated_rto_seconds: int = 60


# ── Catalog ────────────────────────────────────────────────────────────────────

STRATEGY_CATALOG: dict[str, list[RecoveryStrategy]] = {
    "container_crash": [
        RecoveryStrategy(
            name="restart_container",
            steps=[
                "Stop the resilience-web-server container",
                "Start the resilience-web-server container",
                "Wait for /health endpoint to return 200",
            ],
            estimated_rto_seconds=30,
        ),
        RecoveryStrategy(
            name="restore_from_backup",
            steps=[
                "Pull latest backup from resilience-backup-store",
                "Restore backup to resilience-web-server volume",
                "Restart the resilience-web-server container",
                "Verify /health endpoint returns 200",
            ],
            estimated_rto_seconds=120,
        ),
    ],
    "oom_kill": [
        RecoveryStrategy(
            name="restart_container",
            steps=[
                "Restart the OOM-killed container with memory limit increased",
                "Verify /health endpoint returns 200",
            ],
            estimated_rto_seconds=30,
        ),
    ],
    "database_connection_lost": [
        RecoveryStrategy(
            name="restart_container",
            steps=[
                "Restart the resilience-database container",
                "Re-run connection pool probe",
                "Verify downstream services can reach the database",
            ],
            estimated_rto_seconds=45,
        ),
        RecoveryStrategy(
            name="restore_from_backup",
            steps=[
                "Restore database volume from latest backup",
                "Restart the resilience-database container",
                "Verify connections accepted",
            ],
            estimated_rto_seconds=180,
        ),
    ],
    "disk_full": [
        RecoveryStrategy(
            name="restore_from_backup",
            steps=[
                "Free disk space by pruning old logs and temp files",
                "Restore service from clean backup if data corrupt",
                "Restart affected container",
            ],
            estimated_rto_seconds=90,
        ),
    ],
    "network_partition": [
        RecoveryStrategy(
            name="restart_container",
            steps=[
                "Restart Docker network bridge",
                "Restart affected containers",
                "Re-verify inter-service connectivity",
            ],
            estimated_rto_seconds=20,
        ),
    ],
    "process_hang": [
        RecoveryStrategy(
            name="restart_container",
            steps=[
                "Kill the hung process inside the container",
                "Restart the container",
                "Verify service responds within 10 s",
            ],
            estimated_rto_seconds=15,
        ),
    ],
    "unknown": [
        RecoveryStrategy(
            name="restart_container",
            steps=[
                "Attempt generic container restart as first-pass recovery",
                "Collect logs for manual review",
            ],
            estimated_rto_seconds=30,
        ),
        RecoveryStrategy(
            name="restore_from_backup",
            steps=[
                "Restore from last-known-good backup",
                "Restart affected containers",
                "Escalate for manual review",
            ],
            estimated_rto_seconds=180,
        ),
    ],
}


def get_strategies_for(root_cause: str) -> list[RecoveryStrategy]:
    """Return strategy list for *root_cause*, falling back to 'unknown'."""
    return STRATEGY_CATALOG.get(root_cause, STRATEGY_CATALOG["unknown"])


def get_strategy(name: str, root_cause: str) -> RecoveryStrategy | None:
    """Return a specific strategy by name within a root_cause bucket."""
    for s in get_strategies_for(root_cause):
        if s.name == name:
            return s
    return None
