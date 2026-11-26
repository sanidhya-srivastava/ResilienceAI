"""Docker operation tools used by RecoverAgent.

In MOCK_MODE all operations succeed instantly without touching Docker.
In real mode wraps docker-py SDK calls.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


@dataclass
class OpResult:
    success: bool
    action: str
    service: str
    detail: str = ""
    timestamp: str = field(default_factory=lambda: _utcnow())


def restart_container(service: str) -> OpResult:
    """Stop + start a container by its compose service name."""
    if _is_mock_mode():
        return OpResult(
            success=True,
            action="restart",
            service=service,
            detail=f"[MOCK] Container '{service}' restarted successfully",
        )
    try:
        import docker  # noqa: PLC0415
        client = docker.from_env()
        container = client.containers.get(service)
        container.restart(timeout=30)
        # Wait up to 15 s for it to be running
        for _ in range(15):
            container.reload()
            if container.status == "running":
                break
            time.sleep(1)
        running = container.status == "running"
        return OpResult(
            success=running,
            action="restart",
            service=service,
            detail=f"Container status after restart: {container.status}",
        )
    except Exception as exc:
        return OpResult(success=False, action="restart", service=service, detail=str(exc))


def restore_from_backup(service: str) -> OpResult:
    """Restore service data from the latest backup in the backup-store container."""
    if _is_mock_mode():
        return OpResult(
            success=True,
            action="restore_backup",
            service=service,
            detail=f"[MOCK] Backup for '{service}' restored successfully",
        )
    try:
        import docker  # noqa: PLC0415
        client = docker.from_env()
        backup_container = client.containers.get("resilience-backup-store")
        exit_code, output = backup_container.exec_run(
            f"tar -xzf /backups/{service}-backup-latest.tar.gz -C /var/restore/"
        )
        success = exit_code == 0
        return OpResult(
            success=success,
            action="restore_backup",
            service=service,
            detail=output.decode() if output else "No output",
        )
    except Exception as exc:
        return OpResult(success=False, action="restore_backup",
                        service=service, detail=str(exc))


def cleanup_disk(service: str) -> OpResult:
    """Prune temporary fill files and stale logs inside *service*."""
    if _is_mock_mode():
        return OpResult(
            success=True,
            action="cleanup_disk",
            service=service,
            detail=f"[MOCK] Pruned temporary fill files on '{service}'",
        )
    try:
        import docker  # noqa: PLC0415
        client = docker.from_env()
        container = client.containers.get(service)
        exit_code, output = container.exec_run(["sh", "-c", "rm -f /tmp/disk_fill.bin"])
        return OpResult(
            success=exit_code == 0,
            action="cleanup_disk",
            service=service,
            detail=output.decode("utf-8", errors="replace") if output else "Disk pruned",
        )
    except Exception as exc:
        return OpResult(success=False, action="cleanup_disk",
                        service=service, detail=str(exc))


def _utcnow() -> str:
    from backend.simulator.utils import utcnow  # noqa: PLC0415
    return utcnow()


def _is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").lower() == "true"
