"""Health-check tool — polls each simulated service endpoint.

In MOCK_MODE returns pre-canned results without hitting Docker or HTTP.
In real mode:
  - web-server  → HTTP GET http://localhost:8080/health
  - database    → subprocess pg_isready (or SQLite probe)
  - backup-store→ Docker inspect container exit-code
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass
class HealthResult:
    service: str
    healthy: bool
    status: str          # e.g. "running", "exited", "unreachable"
    error: str = ""


# Container names as defined in docker-compose.yml
_SERVICE_MAP = {
    "resilience-web-server": "http://localhost:8080/health",
    "resilience-database": None,   # probed via pg_isready
    "resilience-backup-store": None,   # probed via Docker inspect
}

_MOCK_RESULTS: dict[str, HealthResult] = {
    "resilience-web-server": HealthResult(
        service="resilience-web-server",
        healthy=False,
        status="exited",
        error="Connection refused — container not running",
    ),
    "resilience-database": HealthResult(
        service="resilience-database",
        healthy=True,
        status="running",
    ),
    "resilience-backup-store": HealthResult(
        service="resilience-backup-store",
        healthy=True,
        status="running",
    ),
}


def check_service_health(service_name: str) -> HealthResult:
    """Return a HealthResult for *service_name*.

    Falls back to MOCK data when MOCK_MODE=true (default).
    """
    if _is_mock_mode():
        return _MOCK_RESULTS.get(
            service_name,
            HealthResult(service=service_name, healthy=False, status="unknown"),
        )
    return _check_live(service_name)


def check_all_services() -> dict[str, HealthResult]:
    """Return HealthResult for every known service."""
    return {name: check_service_health(name) for name in _SERVICE_MAP}


# ── Live implementations ───────────────────────────────────────────────────────

def _check_live(service_name: str) -> HealthResult:
    if service_name == "resilience-web-server":
        return _http_check(service_name, "http://localhost:8080/health")
    if service_name == "resilience-database":
        return _pg_check(service_name)
    if service_name == "resilience-backup-store":
        return _docker_inspect_check(service_name)
    return HealthResult(service=service_name, healthy=False, status="unknown",
                        error=f"No health probe defined for '{service_name}'")


def _http_check(service_name: str, url: str) -> HealthResult:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=3) as resp:
            if resp.status == 200:
                return HealthResult(service=service_name, healthy=True, status="running")
            return HealthResult(service=service_name, healthy=False,
                                status="degraded", error=f"HTTP {resp.status}")
    except Exception as exc:
        return HealthResult(service=service_name, healthy=False,
                            status="unreachable", error=str(exc))


def _pg_check(service_name: str) -> HealthResult:
    try:
        result = subprocess.run(
            ["pg_isready", "-h", "localhost", "-p", "5432"],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            return HealthResult(service=service_name, healthy=True, status="running")
        return HealthResult(service=service_name, healthy=False,
                            status="not_ready", error=result.stdout.decode())
    except FileNotFoundError:
        # pg_isready not installed; fall back to Docker inspect
        return _docker_inspect_check(service_name)
    except Exception as exc:
        return HealthResult(service=service_name, healthy=False,
                            status="unreachable", error=str(exc))


def _docker_inspect_check(service_name: str) -> HealthResult:
    try:
        import docker  # noqa: PLC0415
        client = docker.from_env()
        container = client.containers.get(service_name)
        running = container.status == "running"
        return HealthResult(
            service=service_name,
            healthy=running,
            status=container.status,
        )
    except Exception as exc:
        return HealthResult(service=service_name, healthy=False,
                            status="unreachable", error=str(exc))


def _is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").lower() == "true"
