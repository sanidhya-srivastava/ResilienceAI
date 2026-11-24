# ResilienceAI – Complete Implementation Plan

**Version:** 1.0  
**Date:** 2026-11-24  
**Mode:** New Product — Phase 1 MVP (server crash scenario, full agent loop, live dashboard)  
**Status:** Ready for implementation

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  React + Vite Dashboard (port 5173)                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐│
│  │ Scenario     │ │ Agent Status │ │ Recovery Metrics / Timeline  ││
│  │ Selector     │ │ Live Feed    │ │ (Recharts)                   ││
│  └──────────────┘ └──────────────┘ └──────────────────────────────┘│
│           │ HTTP                       │ WebSocket                  │
└───────────┼───────────────────────────┼────────────────────────────┘
            │                           │
┌───────────▼───────────────────────────▼────────────────────────────┐
│  FastAPI Backend (port 8000)                                        │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ /disaster/*    │  │ /status/*        │  │ WebSocket /ws/live  │  │
│  │ (trigger)      │  │ (incident log)   │  │ (agent state push)  │  │
│  └────────┬───────┘  └──────────────────┘  └────────────────────┘  │
│           │                                                          │
│  ┌────────▼────────────────────────────────────────────────────┐    │
│  │ LangGraph RecoveryGraph                                      │    │
│  │                                                              │    │
│  │  [Monitor] → [Diagnose] → [Plan] → [Recover] → [Verify]     │    │
│  │                 ↑                                   │         │    │
│  │                 └──────────── (replan loop) ────────┘         │    │
│  └───────────────────────────────────────────────────────────────┘   │
│           │                           │                               │
│  ┌────────▼──────────┐   ┌────────────▼──────────────────────────┐  │
│  │ Ollama / Mock     │   │ SQLite (incidents.db)                 │  │
│  │ (Qwen 2.5 3B)     │   │ - incidents, agent_actions, metrics   │  │
│  └───────────────────┘   └───────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
            │
┌───────────▼────────────────────────────────────────────────────────┐
│  Docker Compose Simulated Infrastructure                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ web-server      │  │ database        │  │ backup-store    │    │
│  │ (nginx:alpine)  │  │ (postgres:15)   │  │ (alpine + data) │    │
│  │ port 8080       │  │ port 5432       │  │ (volume)        │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Does NOT own |
|-----------|---------------|--------------|
| Docker Compose infra | Run simulated services; accept kill/start commands from backend | Disaster logic, agent logic |
| Disaster Simulator | Inject failures via Docker API; expose REST endpoints to trigger them | Recovery logic |
| LangGraph pipeline | Orchestrate agent execution in the correct sequence; manage state | UI, HTTP routing, DB writes |
| Each agent | One specific action (monitor/diagnose/plan/recover/verify); write its result to RecoveryState | Calling the next agent (graph does this) |
| FastAPI backend | HTTP routing, WebSocket push, DB writes, orchestrating pipeline runs | Agent logic, UI rendering |
| React dashboard | Display state received from backend; send trigger commands | Business logic |
| SQLite | Persist incident log and agent actions | Nothing else |

### Shared State Contract (`RecoveryState`)

```python
class RecoveryState(TypedDict):
    # Set at start
    incident_id: str
    scenario: str                    # e.g. "server_crash"
    triggered_at: str                # ISO timestamp

    # Set by Monitor Agent
    affected_services: list[str]     # e.g. ["web-server"]
    health_metrics: dict             # {service: {status, cpu, mem}}
    anomaly_detected: bool

    # Set by Diagnose Agent
    root_cause: str                  # enum: "container_crash" | "oom_kill" | ...
    severity: str                    # "critical" | "high" | "medium" | "low"
    diagnosis_confidence: float      # 0.0–1.0

    # Set by Plan Agent
    recovery_strategy: str           # enum: "restart_container" | "restore_backup" | ...
    recovery_steps: list[str]        # ordered list of action descriptions
    estimated_rto_seconds: int

    # Set by Recover Agent
    actions_taken: list[dict]        # [{action, timestamp, success, detail}]
    recovery_attempted: bool
    recovery_success: bool

    # Set by Verify Agent
    verification_passed: bool
    post_recovery_metrics: dict
    replan_required: bool            # True if verify fails; triggers loop back to Plan
    replan_count: int                # guard against infinite loops (max 3)

    # Set by backend/graph runner
    completed_at: str | None
    total_duration_seconds: float | None
```

---

## Implementation Units (Phase 1 MVP)

Units are grouped into tracks that can be developed in parallel after their dependencies are met.

---

### Unit 1: Project Scaffold and Repository Setup

**Goal:** Create the directory structure, base configuration files, and development tooling so all subsequent units have a consistent foundation.

**Requirements trace:** All requirements (foundation for every other unit)

**Dependencies:** None

**Files:**
- `README.md` — project overview, quickstart, architecture diagram placeholder
- `docker-compose.yml` — defines all containers (backend, frontend, web-server, database, backup-store, ollama)
- `docker-compose.override.yml` — development overrides (volume mounts for hot reload)
- `backend/` — Python package root
- `backend/requirements.txt` — langgraph, fastapi, uvicorn, pydantic, python-dotenv, httpx, psutil, pytest, pytest-asyncio
- `backend/.env.example` — OLLAMA_HOST, OLLAMA_MODEL, MOCK_MODE, DATABASE_URL
- `frontend/` — Vite + React root (created via `pnpm create vite`)
- `frontend/package.json` — react, react-dom, zustand, recharts, tailwindcss, vitest
- `Makefile` — `make dev`, `make test`, `make lint`, `make demo` (runs mock mode)
- `.gitignore` — standard Python + Node ignores
- `docs/architecture.md` — Mermaid diagram of the system (copy from plan)

**Approach:**
1. Create directory tree: `backend/{agents,api,db,simulator,graph}/`, `frontend/src/{components,stores,api}/`
2. Write `docker-compose.yml` with six services: `backend` (Python FastAPI), `frontend` (Vite dev server), `web-server` (nginx:alpine), `app-database` (postgres:15-alpine), `backup-store` (alpine with a data volume), `ollama` (ollama/ollama)
3. Write `backend/requirements.txt`
4. Bootstrap frontend with `pnpm create vite frontend -- --template react-ts`, then add Tailwind, Zustand, Recharts
5. Write `Makefile` with named targets
6. Write `.env.example` with all required variables and their defaults

**Patterns:** Standard Python package layout. Vite default structure. No custom patterns yet — this unit establishes the patterns.

**Test scenarios:**
- [ ] Happy path: `docker-compose up` starts all containers without port conflicts
- [ ] `make dev` starts backend and frontend with hot reload working
- [ ] `make demo` starts with `MOCK_MODE=true` and exits cleanly
- [ ] `.env.example` contains every variable referenced in code (lint check)

**Verification:** All containers start, `curl localhost:8000/health` returns `{"status": "ok"}`, `localhost:5173` loads a blank React page.

**Planning-time unknowns:**
- Ollama container memory requirements on the developer's machine — Deferred to implementation (use `deploy.resources` in compose if needed)

---

### Unit 2: Simulated Infrastructure Containers

**Goal:** Define the three simulated infrastructure containers (web-server, database, backup-store) with health checks and controlled failure modes.

**Requirements trace:** R1 (infrastructure simulation), R2 (disaster scenarios require killable targets)

**Dependencies:** Unit 1

**Files:**
- `infra/web-server/Dockerfile` — nginx:alpine with a simple HTML health endpoint
- `infra/web-server/nginx.conf` — serves `/health` returning `{"status": "running"}`
- `infra/database/init.sql` — creates a `recovery_test` database with a sample `services` table
- `infra/backup-store/Dockerfile` — alpine with a directory `/backups/` pre-populated with a tar backup file
- `infra/backup-store/seed-backup.sh` — creates `/backups/web-server-backup-latest.tar.gz` at container start
- `docker-compose.yml` (update) — add `healthcheck` entries for all three containers; add named volumes

**Approach:**
1. `web-server` container: nginx with one location block serving `/health` as a JSON response from a static file. The monitoring agent pings this endpoint. When the container is stopped (simulated crash), the endpoint becomes unreachable — this is the failure signal.
2. `app-database` container: postgres:15-alpine with an `init.sql` that creates a table with a few rows. The monitoring agent checks `pg_isready`. When stopped, the database becomes unreachable.
3. `backup-store` container: alpine that creates a `.tar.gz` file in `/backups/` on startup. The backup file contains a copy of the nginx static files and a database dump. The recovery agent will `docker cp` from this container.
4. Add health checks to compose: `test: ["CMD", "curl", "-f", "http://localhost/health"]` for web-server, `test: ["CMD", "pg_isready", "-U", "postgres"]` for database.

**Patterns:** Docker Compose health checks. Named volumes for backup persistence. No custom tooling.

**Test scenarios:**
- [ ] Happy path: all three containers start and health checks pass within 30 seconds
- [ ] Simulated crash: `docker stop resilience-web-server` causes health check to fail; container does not auto-restart (set `restart: "no"` in compose)
- [ ] Backup accessible: `docker exec resilience-backup-store ls /backups/` shows the backup file
- [ ] Database accessible: `docker exec resilience-database pg_isready -U postgres` returns success

**Verification:** All three containers show `healthy` in `docker-compose ps`. Stopping one and checking again shows `unhealthy` / `exited` without auto-restart.

**Planning-time unknowns:** None — all decisions made above.

---

### Unit 3: SQLite Database Layer

**Goal:** Create the persistence layer for incident logs, agent actions, and recovery metrics with a clean async interface.

**Requirements trace:** R3 (incident persistence), R6 (metrics for evaluation)

**Dependencies:** Unit 1

**Files:**
- `backend/db/models.py` — SQLAlchemy models: `Incident`, `AgentAction`, `RecoveryMetrics`
- `backend/db/database.py` — async SQLite engine setup, `get_db` dependency
- `backend/db/repository.py` — `IncidentRepository`, `ActionRepository`, `MetricsRepository` with typed methods
- `backend/db/migrations/001_initial.sql` — DDL for all tables
- `backend/tests/test_db.py` — unit tests for repository methods

**Approach:**

Schema:
```sql
-- incidents table
CREATE TABLE incidents (
    id TEXT PRIMARY KEY,           -- UUID
    scenario TEXT NOT NULL,
    triggered_at TEXT NOT NULL,    -- ISO timestamp
    completed_at TEXT,
    status TEXT NOT NULL,          -- "in_progress" | "recovered" | "failed"
    total_duration_seconds REAL
);

-- agent_actions table
CREATE TABLE agent_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    agent_name TEXT NOT NULL,      -- "monitor" | "diagnose" | "plan" | "recover" | "verify"
    action_type TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    success INTEGER NOT NULL,      -- 0 or 1 (SQLite boolean)
    duration_ms INTEGER,
    timestamp TEXT NOT NULL
);

-- recovery_metrics table
CREATE TABLE recovery_metrics (
    incident_id TEXT PRIMARY KEY REFERENCES incidents(id),
    mttr_seconds REAL,
    detection_time_seconds REAL,
    diagnosis_time_seconds REAL,
    planning_time_seconds REAL,
    recovery_time_seconds REAL,
    verification_time_seconds REAL,
    replan_count INTEGER DEFAULT 0,
    recovery_strategy TEXT,
    success INTEGER NOT NULL
);
```

Use `aiosqlite` for async SQLite access. Repositories are thin — no ORM magic, plain SQL queries. Each repository method takes an `aiosqlite.Connection` and returns typed dataclasses.

**Patterns:** Repository pattern. Typed dataclasses for return values (not raw dicts). `async with database.connect() as conn:` pattern throughout.

**Test scenarios:**
- [ ] Happy path: create an incident, log 5 agent actions, write metrics — all readable back correctly
- [ ] Nil/empty: querying a non-existent incident_id returns `None`, not an exception
- [ ] Error path: attempting to log an action for a non-existent incident_id raises `IntegrityError`
- [ ] Concurrent writes: two simultaneous action inserts for the same incident do not corrupt data (WAL mode)

**Verification:** `pytest backend/tests/test_db.py` passes all tests. `sqlite3 incidents.db .schema` shows correct table definitions.

**Planning-time unknowns:** None.

---

### Unit 4: Disaster Simulator

**Goal:** Implement the disaster injection engine that can trigger, monitor, and resolve simulated failures on the Docker containers.

**Requirements trace:** R1 (disaster simulation), R2 (server crash scenario)

**Dependencies:** Unit 2

**Files:**
- `backend/simulator/docker_client.py` — thin wrapper around `docker` Python SDK: `stop_container`, `start_container`, `get_container_status`, `get_container_health`
- `backend/simulator/scenarios.py` — `ScenarioRegistry`, `ServerCrashScenario` class
- `backend/simulator/base.py` — `BaseScenario` abstract class with `inject()`, `resolve()`, `describe()` methods
- `backend/simulator/schemas.py` — Pydantic models: `ScenarioInfo`, `InjectionResult`, `ResolutionResult`
- `backend/tests/test_simulator.py` — unit tests with Docker mocked

**Approach:**

```python
# base.py
class BaseScenario(ABC):
    name: str
    description: str
    affected_services: list[str]
    
    @abstractmethod
    async def inject(self) -> InjectionResult: ...
    
    @abstractmethod
    async def resolve(self) -> ResolutionResult: ...
    
    def describe(self) -> ScenarioInfo: ...

# scenarios.py — ServerCrashScenario
class ServerCrashScenario(BaseScenario):
    name = "server_crash"
    description = "Stops the web-server container, simulating a process crash."
    affected_services = ["resilience-web-server"]
    
    async def inject(self) -> InjectionResult:
        await docker_client.stop_container("resilience-web-server")
        return InjectionResult(
            scenario=self.name,
            timestamp=utcnow(),
            affected=self.affected_services,
            success=True
        )
    
    async def resolve(self) -> ResolutionResult:
        await docker_client.start_container("resilience-web-server")
        # Wait for health check to pass (max 30s)
        ...
```

`ScenarioRegistry` is a dict keyed by scenario name. Adding a new scenario (Phase 2) requires only: define a new class + register it. No changes to the router or agent code.

Mock mode: `docker_client.py` checks `MOCK_MODE` env var and returns synthetic results without touching Docker. This is the `--mock` demo path.

**Patterns:** Strategy pattern for scenarios. Factory/registry for lookup. Dependency-injected Docker client for testability.

**Test scenarios:**
- [ ] Happy path: `ServerCrashScenario.inject()` with mock client returns `InjectionResult(success=True)`
- [ ] Happy path: `ServerCrashScenario.resolve()` with mock client returns `ResolutionResult(success=True)`
- [ ] Error path: `inject()` on an already-stopped container returns `success=False` with error detail (doesn't throw)
- [ ] Registry lookup: `ScenarioRegistry.get("server_crash")` returns the right class; `get("unknown")` raises `KeyError`

**Verification:** `pytest backend/tests/test_simulator.py` passes. Calling `inject()` in real mode stops the web-server container (visible in `docker ps`).

**Planning-time unknowns:**
- Docker socket permission on Windows (might need `//./pipe/docker_engine`) — Deferred to implementation; Docker SDK handles this automatically on Windows.

---

### Unit 5: LangGraph State Graph and Agent Interfaces

**Goal:** Define the `RecoveryGraph` state machine, the `RecoveryState` TypedDict, and the abstract agent interface that all five agents implement.

**Requirements trace:** R4 (multi-agent pipeline), R5 (agent coordination)

**Dependencies:** Unit 1, Unit 3

**Files:**
- `backend/graph/state.py` — `RecoveryState` TypedDict (full schema from architecture section)
- `backend/graph/base_agent.py` — `BaseAgent` abstract class
- `backend/graph/graph.py` — `build_recovery_graph()` function, conditional edges
- `backend/graph/runner.py` — `GraphRunner.run(scenario, incident_id, ws_callback)` async method
- `backend/graph/mock_responses.py` — deterministic fixture responses for all 5 agents (used when `MOCK_MODE=true`); **critical for demo without Ollama**
- `backend/tests/test_graph.py` — graph structure tests (nodes exist, edges correct, state flows)

**Approach:**

```python
# graph.py
from langgraph.graph import StateGraph, END

def build_recovery_graph(agents: AgentContainer) -> CompiledGraph:
    graph = StateGraph(RecoveryState)
    
    # Add nodes — each node is a callable that takes RecoveryState and returns partial RecoveryState
    graph.add_node("monitor", agents.monitor.run)
    graph.add_node("diagnose", agents.diagnose.run)
    graph.add_node("plan", agents.plan.run)
    graph.add_node("recover", agents.recover.run)
    graph.add_node("verify", agents.verify.run)
    
    # Linear edges
    graph.set_entry_point("monitor")
    graph.add_edge("monitor", "diagnose")
    graph.add_edge("diagnose", "plan")
    graph.add_edge("plan", "recover")
    graph.add_edge("recover", "verify")
    
    # Conditional edge from verify: loop back to plan or finish
    graph.add_conditional_edges(
        "verify",
        should_replan,          # returns "plan" or END
        {"plan": "plan", END: END}
    )
    
    return graph.compile(checkpointer=MemorySaver())

def should_replan(state: RecoveryState) -> str:
    if state["replan_required"] and state["replan_count"] < 3:
        return "plan"
    return END
```

```python
# base_agent.py
class BaseAgent(ABC):
    name: str
    
    @abstractmethod
    async def run(self, state: RecoveryState) -> dict:
        """Return a partial dict of RecoveryState fields to update."""
        ...
    
    async def _call_llm(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        """Calls Ollama or returns mock response based on MOCK_MODE."""
        ...
    
    def _log_action(self, state: RecoveryState, output: dict, success: bool, duration_ms: int) -> None:
        """Writes to agent_actions table. Called by all agents."""
        ...
```

`GraphRunner` runs the compiled graph, injects a WebSocket callback so each agent calls `ws_callback(agent_name, partial_state)` after completing. The backend then pushes this to connected WebSocket clients.

**Patterns:** Each agent returns a `dict` (partial state update), not a modified copy of full state — LangGraph merges these automatically. All agents share the same `_call_llm` and `_log_action` base methods.

**Test scenarios:**
- [ ] Happy path: graph compiles without errors, all 5 nodes are present
- [ ] State flow: mock agents, run graph end-to-end, verify state has all required fields populated
- [ ] Replan loop: `verify` agent returns `replan_required=True`, graph re-enters `plan` node; after 3 loops, terminates at END
- [ ] Replan guard: with `replan_count >= 3`, graph terminates at END even if `replan_required=True`

**Verification:** `pytest backend/tests/test_graph.py` passes. Graph visualization (via LangGraph Studio or `graph.get_graph().print_ascii()`) shows correct topology.

**Planning-time unknowns:** None.

---

### Unit 6: Monitor Agent

**Goal:** Implement the Monitor Agent, which checks the health of all simulated services and populates the `affected_services` and `health_metrics` fields in `RecoveryState`.

**Requirements trace:** R4, R5 (Monitoring Agent responsibility)

**Dependencies:** Unit 5, Unit 2

**Files:**
- `backend/agents/monitor_agent.py` — `MonitorAgent` class
- `backend/agents/tools/health_check.py` — `check_service_health(service_name) -> HealthResult` tool
- `backend/tests/test_monitor_agent.py` — unit tests

**Approach:**

The Monitor Agent does NOT use the LLM for health checking — checking if a container is running is deterministic. The LLM is only used to summarise and label the anomaly.

```python
class MonitorAgent(BaseAgent):
    name = "monitor"
    
    async def run(self, state: RecoveryState) -> dict:
        start = time.time()
        
        # Step 1: Check all service health (deterministic tool call)
        health_results = await asyncio.gather(*[
            health_check.check_service_health(svc)
            for svc in ALL_MONITORED_SERVICES
        ])
        
        health_metrics = {r.service: r.to_dict() for r in health_results}
        affected = [r.service for r in health_results if not r.healthy]
        anomaly_detected = len(affected) > 0
        
        # Step 2: LLM summarises anomaly (only if anomaly detected)
        if anomaly_detected:
            summary_prompt = build_monitor_summary_prompt(health_metrics, affected)
            # LLM output: {"anomaly_description": str, "urgency": "critical"|"high"|"medium"}
            llm_output = await self._call_llm(summary_prompt, MonitorSummarySchema)
        
        duration_ms = int((time.time() - start) * 1000)
        result = {
            "affected_services": affected,
            "health_metrics": health_metrics,
            "anomaly_detected": anomaly_detected,
        }
        await self._log_action(state, result, success=True, duration_ms=duration_ms)
        return result
```

`check_service_health` does:
- For web-server: HTTP GET `http://resilience-web-server/health` with 2s timeout
- For database: `pg_isready` check via `asyncio.create_subprocess_exec`
- For backup-store: `docker inspect` container status

Mock mode: `check_service_health` returns pre-canned `HealthResult` objects defined in a mock fixtures file.

**MonitorSummarySchema:**
```python
class MonitorSummarySchema(BaseModel):
    anomaly_description: str
    urgency: Literal["critical", "high", "medium", "low"]
```

**Patterns:** Deterministic tool first, LLM for summarisation only. Structured output schema. Async parallel health checks.

**Test scenarios:**
- [ ] Happy path: all services healthy → `affected_services=[]`, `anomaly_detected=False`
- [ ] Server crash: web-server health check fails → `affected_services=["resilience-web-server"]`, `anomaly_detected=True`
- [ ] All down: all three services fail → `affected_services` contains all three
- [ ] Tool timeout: health check takes > 2s → returns `HealthResult(healthy=False, error="timeout")` without raising

**Verification:** Run graph in mock mode with `ServerCrashScenario` pre-injected; monitor agent returns `affected_services=["resilience-web-server"]`.

**Planning-time unknowns:** None.

---

### Unit 7: Diagnose Agent

**Goal:** Implement the Diagnose Agent, which analyses the health metrics and determines the root cause and severity of the incident.

**Requirements trace:** R4, R5 (Diagnosis Agent responsibility)

**Dependencies:** Unit 5, Unit 6

**Files:**
- `backend/agents/diagnose_agent.py` — `DiagnoseAgent` class
- `backend/agents/prompts/diagnose_prompt.py` — prompt template
- `backend/tests/test_diagnose_agent.py` — unit tests

**Approach:**

The Diagnose Agent IS primarily LLM-driven, but with constrained output:

```python
class DiagnosisSchema(BaseModel):
    root_cause: Literal[
        "container_crash",
        "oom_kill", 
        "database_connection_lost",
        "disk_full",
        "network_partition",
        "process_hang",
        "unknown"
    ]
    severity: Literal["critical", "high", "medium", "low"]
    diagnosis_confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str  # 1-2 sentences; not shown in UI but logged for debugging
```

```python
class DiagnoseAgent(BaseAgent):
    name = "diagnose"
    
    async def run(self, state: RecoveryState) -> dict:
        start = time.time()
        
        prompt = build_diagnosis_prompt(
            affected_services=state["affected_services"],
            health_metrics=state["health_metrics"],
            scenario=state["scenario"]  # gives the LLM a hint; in real use this would be absent
        )
        
        diagnosis = await self._call_llm(prompt, DiagnosisSchema)
        
        result = {
            "root_cause": diagnosis.root_cause,
            "severity": diagnosis.severity,
            "diagnosis_confidence": diagnosis.diagnosis_confidence,
        }
        await self._log_action(state, result, success=True, duration_ms=...)
        return result
```

**Diagnosis prompt structure:**
```
You are a system reliability engineer analysing infrastructure failures.

CURRENT HEALTH METRICS:
{json.dumps(health_metrics, indent=2)}

AFFECTED SERVICES: {affected_services}

Based on the health data, classify the root cause into one of these categories:
- container_crash: service process exited unexpectedly
- oom_kill: process killed by OOM killer (high memory pressure)
- database_connection_lost: database unreachable
- disk_full: disk usage > 95%
- network_partition: services unreachable due to network issue
- process_hang: process running but not responding
- unknown: cannot determine cause

Respond ONLY with valid JSON matching this schema:
{DiagnosisSchema.model_json_schema()}
```

**Patterns:** Constrained enum output prevents hallucination of non-existent root causes. Prompt includes the JSON schema explicitly to guide Qwen 2.5 3B.

**Test scenarios:**
- [ ] Happy path: given web-server crash metrics → `root_cause="container_crash"`, `severity="critical"`
- [ ] Confidence threshold: if LLM returns `diagnosis_confidence < 0.5`, log a warning but do not block pipeline
- [ ] Mock mode: returns `DiagnosisSchema(root_cause="container_crash", severity="critical", diagnosis_confidence=0.95, reasoning="...")`
- [ ] Malformed LLM output: if Ollama returns invalid JSON, retry once, then fall back to `root_cause="unknown"`

**Verification:** Agent run in mock mode returns valid `DiagnosisSchema`. Integration test with Ollama returns a valid schema instance.

**Planning-time unknowns:**
- Qwen 2.5 3B reliability at JSON schema output: test early with a one-shot prompt before full integration — Deferred to implementation week 1.

---

### Unit 8: Plan Agent

**Goal:** Implement the Plan Agent, which selects the optimal recovery strategy and generates an ordered list of recovery steps.

**Requirements trace:** R4, R5 (Planning Agent responsibility)

**Dependencies:** Unit 5, Unit 7

**Files:**
- `backend/agents/plan_agent.py` — `PlanAgent` class
- `backend/agents/prompts/plan_prompt.py` — prompt template
- `backend/agents/strategies.py` — `STRATEGY_CATALOG`: maps root causes to candidate strategies
- `backend/tests/test_plan_agent.py` — unit tests

**Approach:**

The strategy catalog is a data structure — not a prompt — that pre-defines which strategies are valid for each root cause. The LLM selects from the valid candidates, not from an open universe:

```python
# strategies.py
STRATEGY_CATALOG: dict[str, list[RecoveryStrategy]] = {
    "container_crash": [
        RecoveryStrategy(
            name="restart_container",
            steps=["Stop container", "Start container", "Wait for health check"],
            estimated_rto_seconds=30
        ),
        RecoveryStrategy(
            name="restore_from_backup",
            steps=["Stop container", "Restore from backup volume", "Start container", "Verify data integrity"],
            estimated_rto_seconds=120
        ),
    ],
    "database_connection_lost": [...],
    # etc.
}
```

```python
class PlanningSchema(BaseModel):
    selected_strategy: Literal["restart_container", "restore_from_backup", ...]
    rationale: str  # 1-2 sentences
    confidence: float = Field(ge=0.0, le=1.0)
```

Plan prompt gives the LLM: root cause, severity, affected services, and the LIST OF VALID STRATEGIES with their descriptions. LLM picks one and justifies it. Plan Agent then looks up the full steps from `STRATEGY_CATALOG`.

Replan logic: on second entry (from verify loop), the state contains the previously tried strategy. Plan prompt appends: "The previous strategy '{strategy}' failed. Select a different strategy."

**Test scenarios:**
- [ ] Happy path: `container_crash` → LLM selects `restart_container` → steps populated from catalog
- [ ] Replan: second run with `recovery_success=False` → LLM selects different strategy
- [ ] Unknown root cause: `root_cause="unknown"` → plan agent selects `restart_container` as default fallback
- [ ] All strategies exhausted: `replan_count=3` → graph terminates before plan agent runs again (guard in graph, not agent)

**Verification:** Plan agent run in mock mode returns `recovery_strategy="restart_container"` and `recovery_steps` matching the catalog definition.

**Planning-time unknowns:** None.

---

### Unit 9: Recover Agent

**Goal:** Implement the Recovery Agent, which executes the recovery steps selected by the Plan Agent using Docker and backup operations.

**Requirements trace:** R4, R5 (Recovery Agent responsibility)

**Dependencies:** Unit 5, Unit 8, Unit 4

**Files:**
- `backend/agents/recover_agent.py` — `RecoverAgent` class
- `backend/agents/tools/docker_ops.py` — `restart_container`, `restore_from_backup`, `copy_backup_data` tools
- `backend/tests/test_recover_agent.py` — unit tests

**Approach:**

The Recovery Agent does NOT use the LLM for execution — recovery actions are deterministic tools. The LLM's job in this agent is only to summarise what happened.

```python
class RecoverAgent(BaseAgent):
    name = "recover"
    
    # Maps strategy names to tool functions
    STRATEGY_HANDLERS: dict[str, Callable] = {
        "restart_container": self._handle_restart,
        "restore_from_backup": self._handle_restore,
    }
    
    async def run(self, state: RecoveryState) -> dict:
        strategy = state["recovery_strategy"]
        handler = self.STRATEGY_HANDLERS.get(strategy)
        
        if handler is None:
            return {"recovery_attempted": True, "recovery_success": False, 
                    "actions_taken": [{"action": "unknown_strategy", "success": False}]}
        
        actions_taken = await handler(state)
        overall_success = all(a["success"] for a in actions_taken)
        
        return {
            "actions_taken": actions_taken,
            "recovery_attempted": True,
            "recovery_success": overall_success,
        }
    
    async def _handle_restart(self, state: RecoveryState) -> list[dict]:
        actions = []
        for service in state["affected_services"]:
            result = await docker_ops.restart_container(service)
            actions.append({
                "action": f"restart:{service}",
                "timestamp": utcnow(),
                "success": result.success,
                "detail": result.detail
            })
        return actions
    
    async def _handle_restore(self, state: RecoveryState) -> list[dict]:
        actions = []
        # 1. Stop the affected container
        # 2. Copy backup data from backup-store container
        # 3. Start the container
        # Each step appended to actions list
        ...
        return actions
```

**Test scenarios:**
- [ ] Happy path: `restart_container` strategy → container restarted successfully → `recovery_success=True`
- [ ] Tool failure: Docker restart fails → `recovery_success=False`, `actions_taken` contains the failure detail
- [ ] Unknown strategy: strategy not in `STRATEGY_HANDLERS` → `recovery_success=False` without crashing
- [ ] Restore from backup: backup file copied to container → container starts with restored data

**Verification:** In real mode, `restart_container` strategy actually restarts the web-server container visible in `docker ps`.

**Planning-time unknowns:**
- `docker cp` for backup restore requires the backup-store container to be running — this must be checked before recovery executes. Deferred to implementation (add a pre-condition check in `_handle_restore`).

---

### Unit 10: Verify Agent

**Goal:** Implement the Verification Agent, which checks whether recovery was successful and decides whether replanning is needed.

**Requirements trace:** R4, R5 (Verification Agent responsibility)

**Dependencies:** Unit 5, Unit 9, Unit 6

**Files:**
- `backend/agents/verify_agent.py` — `VerifyAgent` class
- `backend/tests/test_verify_agent.py` — unit tests

**Approach:**

Verification is primarily deterministic (re-run health checks), with the LLM providing a final pass/fail judgment:

```python
class VerifyAgent(BaseAgent):
    name = "verify"
    
    async def run(self, state: RecoveryState) -> dict:
        # Step 1: Re-run health checks on previously affected services
        post_metrics = {}
        all_healthy = True
        for service in state["affected_services"]:
            result = await health_check.check_service_health(service)
            post_metrics[service] = result.to_dict()
            if not result.healthy:
                all_healthy = False
        
        # Step 2: LLM makes final verdict (considering recovery_success + post health)
        verdict_prompt = build_verify_prompt(state, post_metrics, all_healthy)
        # Schema: {"verification_passed": bool, "replan_required": bool, "verdict_reasoning": str}
        verdict = await self._call_llm(verdict_prompt, VerificationSchema)
        
        return {
            "verification_passed": verdict.verification_passed,
            "post_recovery_metrics": post_metrics,
            "replan_required": verdict.replan_required,
            "replan_count": state["replan_count"] + (1 if verdict.replan_required else 0),
        }
```

**VerificationSchema:**
```python
class VerificationSchema(BaseModel):
    verification_passed: bool
    replan_required: bool
    verdict_reasoning: str
```

Simple invariant: `replan_required` can only be True if `verification_passed` is False. Validate this in the Pydantic model with a `model_validator`.

**Test scenarios:**
- [ ] Happy path: services healthy after recovery → `verification_passed=True`, `replan_required=False`
- [ ] Recovery failed: services still down → `verification_passed=False`, `replan_required=True`
- [ ] Replan guard: `replan_count >= 3` → `replan_required=False` regardless of health (overridden in graph, not agent)
- [ ] Pydantic validator: `replan_required=True` with `verification_passed=True` raises `ValidationError`

**Verification:** Graph completes end-to-end: Monitor → Diagnose → Plan → Recover → Verify → END, with `verification_passed=True` in final state.

**Planning-time unknowns:** None.

---

### Unit 11: FastAPI Backend Routing

**Goal:** Expose all backend functionality via REST endpoints and a WebSocket connection for real-time agent state streaming.

**Requirements trace:** R7 (backend API), R8 (real-time dashboard updates)

**Dependencies:** Unit 3, Unit 4, Unit 5

**Files:**
- `backend/api/main.py` — FastAPI app factory, middleware, router registration
- `backend/api/routers/disaster.py` — disaster trigger and status routes
- `backend/api/routers/incidents.py` — incident history and metrics routes
- `backend/api/routers/websocket.py` — WebSocket connection manager and `/ws/live` endpoint
- `backend/api/schemas.py` — Pydantic request/response models for all routes
- `backend/tests/test_api.py` — API integration tests with `httpx.AsyncClient`

**API Contract:**

```
POST /disaster/trigger
  Body: {"scenario": "server_crash"}
  Response: {"incident_id": "uuid", "status": "triggered", "triggered_at": "ISO"}

GET /disaster/scenarios
  Response: [{"name": str, "description": str, "affected_services": [str]}]

GET /incidents
  Response: [{"id", "scenario", "triggered_at", "status", "total_duration_seconds"}]

GET /incidents/{incident_id}
  Response: full incident with agent_actions and metrics

GET /incidents/{incident_id}/metrics
  Response: RecoveryMetrics for the incident

GET /health
  Response: {"status": "ok", "version": "1.0.0", "mock_mode": bool}

WebSocket /ws/live
  Client connects once. Server pushes:
  {"type": "agent_update", "incident_id": str, "agent": str, "state": partial_RecoveryState, "timestamp": str}
  {"type": "incident_complete", "incident_id": str, "success": bool, "metrics": RecoveryMetrics}
```

**WebSocket connection manager:**
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)
    
    def disconnect(self, ws: WebSocket):
        self.active_connections.remove(ws)
```

`/disaster/trigger` runs the graph in a background task (`asyncio.create_task`) so the HTTP response returns immediately with `incident_id`. The graph runner calls `manager.broadcast()` after each agent completes.

**Patterns:** FastAPI dependency injection for DB sessions. Background tasks for long-running graph. `ConnectionManager` singleton for WebSocket broadcasting.

**Test scenarios:**
- [ ] Happy path: `POST /disaster/trigger` returns 200 with valid `incident_id`
- [ ] Duplicate trigger: triggering while another incident is in-progress returns 409 Conflict
- [ ] WebSocket: client connects, trigger disaster, receives 5+ `agent_update` messages and 1 `incident_complete`
- [ ] Invalid scenario: `POST /disaster/trigger` with `{"scenario": "invalid"}` returns 422
- [ ] Incidents list: after one complete run, `GET /incidents` returns exactly one entry

**Verification:** `pytest backend/tests/test_api.py` passes. Manual: `curl -X POST localhost:8000/disaster/trigger -d '{"scenario":"server_crash"}'` returns incident_id.

**Planning-time unknowns:**
- Concurrent incident handling: MVP allows only one active incident at a time (simpler). Multi-incident support deferred to Phase 2. — Resolved: 409 response for concurrent trigger.

---

### Unit 12: React Dashboard — Core Layout and Stores

**Goal:** Build the React application shell, single Zustand store, and API/WebSocket client layer. No visual components yet — this unit establishes the state management foundation.

**Requirements trace:** R9 (interactive dashboard)

**Dependencies:** Unit 11

**Files:**
- `frontend/src/store.ts` — single Zustand store: incident state, agent states, metrics, connection status, trigger error
- `frontend/src/api.ts` — typed fetch wrapper for REST endpoints + WebSocket client with auto-reconnect
- `frontend/src/App.tsx` — root component with layout skeleton
- `frontend/src/types.ts` — TypeScript interfaces matching backend schemas

**TypeScript types:**
```typescript
interface AgentStatus {
  name: 'monitor' | 'diagnose' | 'plan' | 'recover' | 'verify';
  status: 'pending' | 'running' | 'complete' | 'failed';
  durationMs?: number;
  outputSummary?: string;
}

interface StoreState {
  incidentId: string | null;
  scenario: string | null;
  status: 'idle' | 'running' | 'complete' | 'failed';
  agents: AgentStatus[];
  metrics: RecoveryMetrics | null;
  triggeredAt: string | null;
  isTriggeringDisaster: boolean;  // true from POST send until incident_id received
  triggerError: string | null;    // set on HTTP error; cleared on reset
}
```

**Zustand store pattern:**
```typescript
const useStore = create<StoreState & StoreActions>((set) => ({
  incidentId: null,
  status: 'idle',
  agents: initialAgentStatuses,
  metrics: null,
  isTriggeringDisaster: false,
  triggerError: null,
  
  triggerDisaster: async (scenario: string) => {
    set({ isTriggeringDisaster: true, triggerError: null });
    try {
      const response = await api.triggerDisaster(scenario);
      set({ incidentId: response.incident_id, status: 'running', isTriggeringDisaster: false });
    } catch (err) {
      set({ isTriggeringDisaster: false, triggerError: err.message });
    }
  },
  
  handleAgentUpdate: (update: AgentUpdateMessage) => {
    set((state) => ({
      agents: state.agents.map(a => 
        a.name === update.agent ? { ...a, status: 'complete', ...update.state } : a
      )
    }));
  },
  
  dismissError: () => set({ triggerError: null }),
  reset: () => set({ ...initialState }),
}));
```

**Test scenarios:**
- [ ] Happy path: `triggerDisaster("server_crash")` sets `isTriggeringDisaster=true`, then `incidentId` and `status='running'`
- [ ] Error path: HTTP error sets `triggerError` with message, `isTriggeringDisaster` returns to false
- [ ] WebSocket message: `handleAgentUpdate` with agent name "monitor" updates the monitor agent's status
- [ ] Reset: `reset()` clears all incident state back to idle, including `triggerError`

**Verification:** Vitest unit tests on store actions. `useStore.getState().status === 'idle'` on init.

**Planning-time unknowns:** None.

---

### Unit 13: React Dashboard — UI Components (Scenario Selector, Agent Feed, Metrics Panel)

**Goal:** Build all three dashboard UI panels in one implementation pass: the scenario selector, the live agent feed, and the post-recovery metrics panel.

**Requirements trace:** R9 (scenario selection, agent activity, recovery analytics)

**Dependencies:** Unit 12

**Files:**
- `frontend/src/components/ScenarioSelector.tsx` — scenario cards with select + trigger button
- `frontend/src/components/ScenarioCard.tsx` — individual scenario card (name, description, affected services, severity badge)
- `frontend/src/components/AgentFeed.tsx` — ordered list of agent status cards
- `frontend/src/components/AgentCard.tsx` — individual agent card with status indicator, timing, output summary, aria-label
- `frontend/src/components/MetricsPanel.tsx` — metrics container
- `frontend/src/components/MTTRBreakdown.tsx` — stacked bar chart (Recharts): detection + diagnosis + planning + recovery + verification time
- `frontend/src/components/RecoveryStatus.tsx` — large success/failure indicator with key stats
- `frontend/src/components/ErrorBanner.tsx` — dismissable error banner reading `triggerError` from store
- `frontend/src/hooks/useScenarios.ts` — fetches available scenarios from `GET /disaster/scenarios`
- `frontend/tests/Dashboard.test.tsx` — Vitest component tests for all components

**Approach:**

**Scenario Selector:**
```tsx
export function ScenarioSelector() {
  const { scenarios } = useScenarios();
  const [selected, setSelected] = useState<string | null>(null);
  const { triggerDisaster, status, isTriggeringDisaster } = useStore();
  
  return (
    <>
      <ErrorBanner />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {scenarios.map(scenario => (
          <ScenarioCard key={scenario.name} scenario={scenario}
            isSelected={selected === scenario.name}
            onSelect={() => setSelected(scenario.name)} />
        ))}
        <button
          onClick={() => selected && triggerDisaster(selected)}
          disabled={!selected || status === 'running' || isTriggeringDisaster}
          className="col-span-full ..."
        >
          {isTriggeringDisaster ? '⟳ Initiating...' : 
           status === 'running' ? 'Recovery in progress...' : 'Trigger Disaster'}
        </button>
      </div>
    </>
  );
}
```

MVP shows "Server Crash" as the only enabled scenario. Other 4 show as locked cards with "Coming in Phase 2."

**Agent Feed:**
```tsx
const STATUS_STYLES = {
  pending: 'border-gray-300 bg-gray-50',
  running: 'border-blue-400 bg-blue-50 animate-pulse',
  complete: 'border-green-400 bg-green-50',
  failed: 'border-red-400 bg-red-50',
};

export function AgentCard({ agent }: { agent: AgentStatus }) {
  return (
    <div className={`border-2 rounded-lg p-4 transition-all ${STATUS_STYLES[agent.status]}`}>
      <div className="flex items-center gap-2">
        {/* aria-label prevents screen readers reading raw Unicode */}
        <span aria-label={`${agent.name} agent: ${agent.status}`} className="text-lg">
          {STATUS_ICONS[agent.status]}
        </span>
        <h3 className="font-semibold capitalize">{agent.name} Agent</h3>
        {agent.durationMs && <span className="ml-auto text-sm text-gray-500">{agent.durationMs}ms</span>}
      </div>
      {agent.outputSummary && <p className="mt-2 text-sm text-gray-700">{agent.outputSummary}</p>}
    </div>
  );
}
```

Before first run: all 5 agent cards shown in 'pending' state with subtitle "Waiting for disaster trigger."

**Metrics Panel:**
```tsx
// Only renders when status === 'complete'
const PHASE_COLORS = {
  detection: '#3b82f6', diagnosis: '#8b5cf6',
  planning: '#f59e0b', recovery: '#ef4444', verification: '#10b981'
};

// Recharts BarChart — horizontal stacked bar showing time per phase
```

**Test scenarios:**
- [ ] Scenario selector: loading and rendering cards; trigger button disabled while `isTriggeringDisaster=true`
- [ ] Error banner: `triggerError` set → ErrorBanner visible; dismiss → `triggerError` null, banner hidden
- [ ] Agent feed: all 5 agents show 'pending' on idle; transition to 'complete' on store update
- [ ] Agent aria-labels: each status icon span has `aria-label` with agent name and status
- [ ] Metrics panel: hidden when `status !== 'complete'`; renders correctly with green (success) or red (failure) state
- [ ] Chart: Recharts BarChart renders without errors given valid metrics data

**Verification:** Complete a mock recovery run → all agent cards transition to green, then metrics panel appears with stacked bar chart.

**Planning-time unknowns:** None.

### Unit 14: Integration Testing and End-to-End Verification Integration Testing and End-to-End Verification

**Goal:** Write integration tests that verify the complete system works end-to-end in both mock and real modes, and verify the demo flow.

**Requirements trace:** R12 (testing), all prior requirements

**Dependencies:** All prior units (1–15)

**Files:**
- `backend/tests/test_integration.py` — full graph run tests (mock mode), API + WebSocket integration
- `backend/tests/test_e2e.py` — end-to-end: trigger via API → graph runs → incident logged → metrics correct
- `backend/tests/conftest.py` — pytest fixtures: test database, mock docker client, mock Ollama
- `frontend/tests/e2e/recovery-flow.test.tsx` — Vitest: full UI flow with mocked API and WebSocket

**Key integration tests:**

```python
# test_e2e.py
async def test_full_recovery_loop_mock_mode(client, mock_docker, mock_ollama):
    """Trigger server_crash in mock mode, verify complete incident logged."""
    
    # 1. Trigger disaster
    response = await client.post("/disaster/trigger", json={"scenario": "server_crash"})
    assert response.status_code == 200
    incident_id = response.json()["incident_id"]
    
    # 2. Wait for completion (poll with timeout)
    for _ in range(30):  # max 30 seconds
        await asyncio.sleep(1)
        incident = await client.get(f"/incidents/{incident_id}")
        if incident.json()["status"] != "in_progress":
            break
    
    # 3. Verify incident state
    final = await client.get(f"/incidents/{incident_id}")
    assert final.json()["status"] == "recovered"
    
    # 4. Verify all 5 agent actions logged
    actions = await client.get(f"/incidents/{incident_id}")
    agent_names = {a["agent_name"] for a in final.json()["agent_actions"]}
    assert agent_names == {"monitor", "diagnose", "plan", "recover", "verify"}
    
    # 5. Verify metrics computed
    metrics = await client.get(f"/incidents/{incident_id}/metrics")
    assert metrics.json()["mttr_seconds"] > 0
    assert metrics.json()["success"] == 1
```

**Test scenarios:**
- [ ] Happy path: full recovery loop in mock mode produces a complete incident with metrics
- [ ] Replan loop: mock verify agent returns `replan_required=True` for 2 iterations, then passes on 3rd
- [ ] Max replan guard: mock verify always fails → incident completes with `recovery_success=False` after 3 replans
- [ ] WebSocket stream: connect WS before trigger → receive 5 agent_update events + 1 incident_complete
- [ ] Concurrent prevention: trigger while running → 409 Conflict

**Verification:** `pytest backend/tests/test_e2e.py -v` all pass. `make demo` starts system and completes a mock recovery visible in the browser.

**Planning-time unknowns:** None.

---

### Unit 17: Documentation and Repository Polish

**Goal:** Write all documentation needed for a technical interviewer to understand, run, and evaluate the project without asking questions.

**Requirements trace:** R13 (portfolio readiness)

**Dependencies:** All prior units complete

**Files:**
- `README.md` (overwrite) — final README: badges, 1-min demo GIF, architecture diagram (Mermaid), quickstart, tech stack table, project structure, links to docs
- `docs/architecture.md` — full architecture deep-dive with component diagrams
- `docs/design-decisions.md` — key design decisions and their rationale (references tech-stack.md)
- `docs/agent-reference.md` — per-agent: inputs, outputs, LLM prompt structure, failure modes
- `docs/api-reference.md` — all REST endpoints and WebSocket message types with examples
- `docs/running-locally.md` — step-by-step: install Docker, Ollama, clone, `docker-compose up`, open dashboard
- `CONTRIBUTING.md` — brief: how to add a new scenario (references scenario registry pattern)
- `.github/workflows/ci.yml` — GitHub Actions: `pytest` on push, `pnpm test` on push

**README structure:**
```markdown
# ResilienceAI
> Multi-agent AI disaster recovery simulator built with LangGraph, FastAPI, and React.

[demo GIF]

## What it does
[2-paragraph explanation]

## Architecture
[Mermaid diagram — same as architecture.md]

## Quickstart
```bash
git clone ...
docker-compose up
# Open http://localhost:5173
```

## Tech Stack
[table]

## Project Structure
[annotated tree]

## How it works
[link to docs/architecture.md]
```

**CI pipeline:**
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v --tb=short
        env: {MOCK_MODE: "true", DATABASE_URL: "sqlite:///test.db"}
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - run: pnpm install
        working-directory: frontend
      - run: pnpm test --run
        working-directory: frontend
```

**Test scenarios:**
- [ ] README quickstart: a fresh clone + `docker-compose up` reaches the dashboard (tested on a second machine or VM)
- [ ] CI passes: GitHub Actions green on main branch
- [ ] Demo GIF: mock mode run captured and embedded in README
- [ ] All links in docs resolve (no 404s within the repo)

**Verification:** GitHub repository shows green CI badge on README. README renders correctly on GitHub. `docker-compose up` from a cold clone works within 10 minutes.

**Planning-time unknowns:** None.

---

## Implementation Order and Parallelism

```
Week 1: Foundation
  Unit 1  [Project Scaffold]        ──→ everything depends on this
  Unit 2  [Infra Containers]        ──→ can start in parallel with Unit 1
  Unit 3  [SQLite Layer]            ──→ can start once Unit 1 done

Week 2: Core Backend
  Unit 4  [Disaster Simulator]      ──→ needs Unit 2
  Unit 5  [LangGraph Graph + Base]  ──→ needs Units 1, 3

Week 3: Agents
  Unit 6  [Monitor Agent]           ──→ needs Units 4, 5
  Unit 7  [Diagnose Agent]          ──→ needs Unit 5 (can parallel Unit 6)
  Unit 8  [Plan Agent]              ──→ needs Unit 5 (can parallel Units 6, 7)

Week 4: Remaining Agents + API
  Unit 9  [Recover Agent]           ──→ needs Units 4, 8
  Unit 10 [Verify Agent]            ──→ needs Units 5, 9
  Unit 11 [FastAPI Routing]         ──→ needs Units 3, 4, 5

Week 5: Frontend
  Unit 12 [React Store + API]       ──→ needs Unit 11
  Unit 13 [Dashboard Components]    ──→ needs Unit 12 (all UI in one pass)

Week 6: Integration + Polish
  Unit 14 [Integration Tests]       ──→ needs all prior units
  Unit 15 [Documentation + CI]      ──→ needs Unit 14 passing
```

**Units reduced from 17 to 15 after SCOPE REDUCTION review:**
- Units 13+14+15 merged into one "Dashboard Components" unit (same files, one pass)
- Documentation scope cut to README + running-locally.md + CI only (arch deep-dive deferred to Phase 3)
- `docker-compose.override.yml` removed; single compose file with dev variables

---

## Quality Bar Checklist

- [x] Every unit has a requirements trace
- [x] Dependencies form a DAG (no cycles — verified in implementation order above)
- [x] Every unit has at least 3 test scenarios (most have 4–5)
- [x] No unit touches > 8 files
- [x] No more than 2 new abstractions introduced per unit
- [x] Every planning-time unknown is classified as blocker or deferred
- [x] Handoff completeness: an engineer can implement any unit without inventing product behavior
