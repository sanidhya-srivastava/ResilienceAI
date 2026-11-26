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
        success = result.get("action") in ("stopped",) or result.get("mock") == "true"
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=success,
            detail=result.get("error", ""),
        )

    def resolve(self) -> ResolutionResult:
        result = docker_client.start_container("resilience-web-server")
        success = result.get("action") in ("started",) or result.get("mock") == "true"
        return ResolutionResult(
            scenario=self.name,
            timestamp=utcnow(),
            success=success,
            detail=result.get("error", ""),
        )


class DatabaseOutageScenario(BaseScenario):
    """Simulates PostgreSQL failure so downstream queries fail."""

    name = "database_connection_lost"
    description = (
        "Stops the PostgreSQL container, dropping all database connections while "
        "the web server remains running in a degraded dependency state."
    )
    affected_services = ["resilience-database"]
    severity = "critical"

    def inject(self) -> InjectionResult:
        result = docker_client.stop_container("resilience-database")
        success = result.get("action") in ("stopped",) or result.get("mock") == "true"
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=success,
            detail=result.get("error", ""),
        )

    def resolve(self) -> ResolutionResult:
        result = docker_client.start_container("resilience-database")
        success = result.get("action") in ("started",) or result.get("mock") == "true"
        return ResolutionResult(
            scenario=self.name,
            timestamp=utcnow(),
            success=success,
            detail=result.get("error", ""),
        )


class OOMKillScenario(BaseScenario):
    """Simulates an abrupt kernel OOM kill (SIGKILL / exit 137) on web-server."""

    name = "oom_kill"
    description = (
        "Sends SIGKILL (exit code 137) to web-server to mimic an out-of-memory kill "
        "without graceful socket teardown."
    )
    affected_services = ["resilience-web-server"]
    severity = "high"

    def inject(self) -> InjectionResult:
        result = docker_client.kill_container("resilience-web-server", signal="SIGKILL")
        success = result.get("action") in ("killed",) or result.get("mock") == "true"
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=success,
            detail=result.get("error", ""),
        )

    def resolve(self) -> ResolutionResult:
        result = docker_client.start_container("resilience-web-server")
        success = result.get("action") in ("started",) or result.get("mock") == "true"
        return ResolutionResult(
            scenario=self.name,
            timestamp=utcnow(),
            success=success,
            detail=result.get("error", ""),
        )


class DiskFullScenario(BaseScenario):
    """Tricky failure: container stays up, but scratch storage fills up."""

    name = "disk_full"
    description = (
        "Fills scratch storage inside backup-store with a large dummy file. "
        "Container stays 'running', so naive process restarts do not free disk space."
    )
    affected_services = ["resilience-backup-store"]
    severity = "high"

    def inject(self) -> InjectionResult:
        res = docker_client.exec_in_container(
            "resilience-backup-store",
            "dd if=/dev/zero of=/tmp/disk_fill.bin bs=1M count=64 2>/dev/null || touch /tmp/disk_fill.bin",
        )
        success = res.get("exit_code") == 0 or res.get("mock") == "true"
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=success,
            detail=str(res.get("output", "")),
        )

    def resolve(self) -> ResolutionResult:
        res = docker_client.exec_in_container(
            "resilience-backup-store",
            "rm -f /tmp/disk_fill.bin",
        )
        success = res.get("exit_code") == 0 or res.get("mock") == "true"
        return ResolutionResult(
            scenario=self.name,
            timestamp=utcnow(),
            success=success,
            detail=str(res.get("output", "")),
        )


class CorruptedConfigScenario(BaseScenario):
    """Tricky failure: corrupted nginx config causes restarts to keep failing until restored."""

    name = "corrupted_config"
    description = (
        "Corrupts nginx routing config inside web-server. A simple container restart "
        "fails verification, forcing the Verify -> Plan replan loop to restore from backup."
    )
    affected_services = ["resilience-web-server"]
    severity = "critical"

    def inject(self) -> InjectionResult:
        res = docker_client.exec_in_container(
            "resilience-web-server",
            "cp /etc/nginx/conf.d/default.conf /tmp/default.conf.bak && "
            "echo 'INVALID_DIRECTIVE;' > /etc/nginx/conf.d/default.conf && nginx -s reload",
        )
        # nginx -s reload may exit non-zero because the config is broken — that's expected
        success = res.get("mock") == "true" or "not found" not in str(res.get("output", "")).lower()
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=success,
            detail=str(res.get("output", "")),
        )

    def resolve(self) -> ResolutionResult:
        res = docker_client.exec_in_container(
            "resilience-web-server",
            "if [ -f /tmp/default.conf.bak ]; then mv /tmp/default.conf.bak /etc/nginx/conf.d/default.conf; fi && nginx -s reload",
        )
        success = res.get("exit_code") == 0 or res.get("mock") == "true"
        return ResolutionResult(
            scenario=self.name,
            timestamp=utcnow(),
            success=success,
            detail=str(res.get("output", "")),
        )


class CascadingFailureScenario(BaseScenario):
    """Tricky multi-service outage: DB and web-server drop together; DB must recover first."""

    name = "cascading_failure"
    description = (
        "Simultaneously kills database and web-server. Requires dependency-ordered recovery "
        "(bring PostgreSQL online before restarting web-server)."
    )
    affected_services = ["resilience-database", "resilience-web-server"]
    severity = "critical"

    def inject(self) -> InjectionResult:
        db_res = docker_client.stop_container("resilience-database")
        web_res = docker_client.kill_container("resilience-web-server", signal="SIGKILL")
        ok_db = db_res.get("action") in ("stopped",) or db_res.get("mock") == "true"
        ok_web = web_res.get("action") in ("killed",) or web_res.get("mock") == "true"
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=ok_db and ok_web,
            detail=f"db={db_res.get('action')}, web={web_res.get('action')}",
        )

    def resolve(self) -> ResolutionResult:
        db_res = docker_client.start_container("resilience-database")
        web_res = docker_client.start_container("resilience-web-server")
        ok_db = db_res.get("action") in ("started",) or db_res.get("mock") == "true"
        ok_web = web_res.get("action") in ("started",) or web_res.get("mock") == "true"
        return ResolutionResult(
            scenario=self.name,
            timestamp=utcnow(),
            success=ok_db and ok_web,
            detail=f"db={db_res.get('action')}, web={web_res.get('action')}",
        )


# ---------------------------------------------------------------------------
# Registry — add new scenarios here; nothing else needs to change.
# ---------------------------------------------------------------------------

class ScenarioRegistry:
    """Lookup table mapping scenario names to their classes."""

    _registry: dict[str, type[BaseScenario]] = {
        ServerCrashScenario.name: ServerCrashScenario,
        DatabaseOutageScenario.name: DatabaseOutageScenario,
        OOMKillScenario.name: OOMKillScenario,
        DiskFullScenario.name: DiskFullScenario,
        CorruptedConfigScenario.name: CorruptedConfigScenario,
        CascadingFailureScenario.name: CascadingFailureScenario,
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
