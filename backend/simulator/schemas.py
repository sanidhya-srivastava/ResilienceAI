from __future__ import annotations

from pydantic import BaseModel


class ScenarioInfo(BaseModel):
    """Describes a disaster scenario available for injection."""

    name: str
    description: str
    affected_services: list[str]
    severity: str  # "critical" | "high" | "medium"


class InjectionResult(BaseModel):
    """Result returned after a disaster is injected."""

    scenario: str
    timestamp: str
    affected: list[str]
    success: bool
    detail: str = ""


class ResolutionResult(BaseModel):
    """Result returned after a disaster is manually resolved."""

    scenario: str
    timestamp: str
    success: bool
    detail: str = ""
