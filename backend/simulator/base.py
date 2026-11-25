from __future__ import annotations

from abc import ABC, abstractmethod

from backend.simulator.schemas import InjectionResult, ResolutionResult, ScenarioInfo


class BaseScenario(ABC):
    """Abstract base class for all disaster scenarios."""

    name: str
    description: str
    affected_services: list[str]
    severity: str = "critical"

    @abstractmethod
    def inject(self) -> InjectionResult:
        """Inject the disaster into the simulated infrastructure."""
        ...

    @abstractmethod
    def resolve(self) -> ResolutionResult:
        """Restore the simulated infrastructure to a healthy state."""
        ...

    def describe(self) -> ScenarioInfo:
        """Return metadata describing this scenario."""
        return ScenarioInfo(
            name=self.name,
            description=self.description,
            affected_services=self.affected_services,
            severity=self.severity,
        )
