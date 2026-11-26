from __future__ import annotations

import os

import docker
import docker.errors
from docker import DockerClient


def _get_client() -> DockerClient:
    """Return a Docker SDK client using the local socket."""
    return docker.from_env()


def stop_container(name: str) -> dict[str, str]:
    """Stop a running container by name. Returns status dict."""
    if os.getenv("MOCK_MODE", "true").lower() == "true":
        return {"name": name, "action": "stopped", "mock": "true"}
    client = _get_client()
    try:
        container = client.containers.get(name)
        container.stop(timeout=5)
        return {"name": name, "action": "stopped"}
    except docker.errors.NotFound:
        return {"name": name, "action": "not_found", "error": f"Container '{name}' not found"}
    except docker.errors.APIError as exc:
        return {"name": name, "action": "error", "error": str(exc)}


def start_container(name: str) -> dict[str, str]:
    """Start a stopped container by name. Returns status dict."""
    if os.getenv("MOCK_MODE", "true").lower() == "true":
        return {"name": name, "action": "started", "mock": "true"}
    client = _get_client()
    try:
        container = client.containers.get(name)
        container.start()
        return {"name": name, "action": "started"}
    except docker.errors.NotFound:
        return {"name": name, "action": "not_found", "error": f"Container '{name}' not found"}
    except docker.errors.APIError as exc:
        return {"name": name, "action": "error", "error": str(exc)}


def get_container_status(name: str) -> str:
    """Return container status string: 'running', 'exited', 'not_found', etc."""
    if os.getenv("MOCK_MODE", "true").lower() == "true":
        return "running"
    client = _get_client()
    try:
        container = client.containers.get(name)
        container.reload()
        return container.status  # type: ignore[no-any-return]
    except docker.errors.NotFound:
        return "not_found"
    except docker.errors.APIError:
        return "error"


def get_container_health(name: str) -> str:
    """Return container health string: 'healthy', 'unhealthy', 'none', 'not_found'."""
    if os.getenv("MOCK_MODE", "true").lower() == "true":
        return "healthy"
    client = _get_client()
    try:
        container = client.containers.get(name)
        container.reload()
        health = container.attrs.get("State", {}).get("Health", {})
        return health.get("Status", "none") if health else "none"
    except docker.errors.NotFound:
        return "not_found"
    except docker.errors.APIError:
        return "error"


def kill_container(name: str, signal: str = "SIGKILL") -> dict[str, str]:
    """Send a signal (default SIGKILL, simulating OOM/crash) to a running container."""
    if os.getenv("MOCK_MODE", "true").lower() == "true":
        return {"name": name, "action": "killed", "signal": signal, "mock": "true"}
    client = _get_client()
    try:
        container = client.containers.get(name)
        container.kill(signal=signal)
        return {"name": name, "action": "killed", "signal": signal}
    except docker.errors.NotFound:
        return {"name": name, "action": "not_found", "error": f"Container '{name}' not found"}
    except docker.errors.APIError as exc:
        return {"name": name, "action": "error", "error": str(exc)}


def exec_in_container(name: str, command: str) -> dict[str, str | int]:
    """Execute a shell command inside a running container."""
    if os.getenv("MOCK_MODE", "true").lower() == "true":
        return {"name": name, "exit_code": 0, "output": f"[MOCK] ran: {command}", "mock": "true"}
    client = _get_client()
    try:
        container = client.containers.get(name)
        exit_code, output = container.exec_run(["sh", "-c", command])
        return {
            "name": name,
            "exit_code": int(exit_code),
            "output": output.decode("utf-8", errors="replace") if output else "",
        }
    except docker.errors.NotFound:
        return {"name": name, "exit_code": 1, "output": f"Container '{name}' not found"}
    except docker.errors.APIError as exc:
        return {"name": name, "exit_code": 1, "output": str(exc)}
