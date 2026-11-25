from __future__ import annotations

from backend.simulator import docker_client
from backend.simulator.base import BaseScenario
from backend.simulator.schemas import InjectionResult, ResolutionResult, ScenarioInfo
from backend.simulator.utils import utcnow


class ServerCrashScenario(BaseScenario):
    """Simulates a web server process crash by stopping its container."""

    name = "server_crash"
    description = (
        "Stops the web-server container, simulating an unexpected process crash. "
        "The /health endpoint becomes unreachable until the container is restarted."
    )
    affected_services = ["resilience-web-server"]
    severity = "critical"

    def inject(self) -> InjectionResult:
        result = docker_client.stop_container("resilience-web-server")
        success = result.get("action") in ("stopped", )
        # In mock mode the action is "stopped" with mock=true — treat as success
        if result.get("mock") == "true":
            success = True
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=success,
            detail=result.get("error", ""),
        )

    def resolve(self) -> ResolutionResult:
        result = docker_client.start_container("resilience-web-server")
        success = result.get("action") in ("started",)
        if result.get("mock") == "true":
            success = True
        return ResolutionResult(
            scenario=self.name,
            timestamp=utcnow(),
            success=success,
            detail=result.get("error", ""),
        )


# ---------------------------------------------------------------------------
# Registry — add new scenarios here; nothing else needs to change.
# ---------------------------------------------------------------------------

class ScenarioRegistry:
    """Lookup table mapping scenario names to their classes."""

    _registry: dict[str, type[BaseScenario]] = {
        ServerCrashScenario.name: ServerCrashScenario,
    }

    @classmethod
    def get(cls, name: str) -> BaseScenario:
        """Return an instance of the named scenario, or raise KeyError."""
        if name not in cls._registry:
            available = ", ".join(cls._registry)
            raise KeyError(f"Unknown scenario '{name}'. Available: {available}")
        return cls._registry[name]()

    @classmethod
    def list_all(cls) -> list[ScenarioInfo]:
        """Return ScenarioInfo for every registered scenario."""
        return [cls._registry[name]().describe() for name in cls._registry]
