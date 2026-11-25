"""Smoke tests for the Disaster Simulator (all run in MOCK_MODE=true)."""
from __future__ import annotations

import os

import pytest

os.environ["MOCK_MODE"] = "true"

from backend.simulator.scenarios import ScenarioRegistry, ServerCrashScenario  # noqa: E402


def test_server_crash_inject_succeeds() -> None:
    scenario = ServerCrashScenario()
    result = scenario.inject()
    assert result.success is True
    assert result.scenario == "server_crash"
    assert "resilience-web-server" in result.affected


def test_server_crash_resolve_succeeds() -> None:
    scenario = ServerCrashScenario()
    result = scenario.resolve()
    assert result.success is True
    assert result.scenario == "server_crash"


def test_registry_get_known_scenario() -> None:
    scenario = ScenarioRegistry.get("server_crash")
    assert isinstance(scenario, ServerCrashScenario)


def test_registry_get_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError, match="unknown_scenario"):
        ScenarioRegistry.get("unknown_scenario")


def test_registry_list_all() -> None:
    infos = ScenarioRegistry.list_all()
    names = [i.name for i in infos]
    assert "server_crash" in names


def test_describe_returns_scenario_info() -> None:
    scenario = ServerCrashScenario()
    info = scenario.describe()
    assert info.name == "server_crash"
    assert info.severity == "critical"
    assert len(info.affected_services) > 0
