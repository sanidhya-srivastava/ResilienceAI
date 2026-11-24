# Tech Stack

## Decision Principles

**Boring by default, locally runnable always, cost-zero non-negotiable.** Every choice is validated against: does this run on a developer laptop with no internet and no paid services? Complexity is added only when a simpler option demonstrably fails to meet a requirement. No choice is made speculatively — if a component isn't needed for the MVP, it isn't in the stack.

## Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| AI Model | Ollama + Qwen 2.5 3B | Runs fully locally, zero API cost, sufficient for classification/selection tasks when prompted with structured schemas. Acceptable for MVP. |
| Agent Framework | LangGraph 0.2+ | Purpose-built for stateful multi-agent workflows with cyclic graphs. Native checkpointing (recoverable runs), `interrupt()` for human-in-the-loop, typed `StateGraph`. Significantly better fit than vanilla LangChain chains for this use case. |
| Backend | Python 3.11 + FastAPI | FastAPI is the right choice: async-native, automatic OpenAPI docs, Pydantic models for request/response validation align with LangGraph's typed state. Python is the right language for LangGraph integration. |
| Infrastructure Simulation | Docker Compose | The only practical way to simulate multi-service infrastructure locally without cloud access. Containers provide real process isolation for the simulated "server crash" (kill a container) and database corruption (corrupt a volume file). |
| Database | SQLite | Zero-configuration, file-based, sufficient for incident logs and agent action history. No connection management overhead. If this were a real product, Postgres — but for a local demo, SQLite is correct. |
| Monitoring | Python + psutil | psutil reads real local system metrics (CPU, memory, disk) which can feed the simulated monitoring layer. Keeps the monitoring agent grounded in real data rather than pure simulation. |
| Frontend | React 18 + Vite | Vite is significantly faster to start than CRA. React is correct for a component-driven dashboard with real-time state updates. No SSR needed — this is a local dev tool. |
| Real-time Updates | WebSockets (FastAPI native) | Agent state updates must be pushed to the dashboard without polling. FastAPI's native WebSocket support is the simplest path. No need for Redis pub/sub or Kafka for a local single-user tool. |
| State Management (Frontend) | Zustand | Lighter than Redux for a dashboard this size. Avoids boilerplate. Single store for agent states, incident log, and metrics. |
| Styling | Tailwind CSS | Utility-first, no design system to maintain, fast iteration. Acceptable for a portfolio project where custom design is not the goal. |
| Charting | Recharts | React-native, well-documented, sufficient for MTTR timelines and bar charts. No need for D3 complexity. |
| Version Control | Git + GitHub | Standard. Public repository with clear commit history is table stakes for a portfolio project. |
| Package Management | pip + requirements.txt (backend), pnpm (frontend) | Simple, standard, universally understood. No Poetry or Nx complexity. |
| Testing | pytest (backend), Vitest (frontend) | Standard testing tools for each language. Vitest is Vite-native and faster than Jest for this setup. |

## Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| GPT-4 / Claude via API | Paid, requires internet, violates cost-zero constraint |
| Llama 3 8B or larger | Local inference would be too slow on most developer hardware for a live demo |
| CrewAI instead of LangGraph | Less control over state graph shape; LangGraph's explicit graph definition is better for this architecture where the recovery workflow must be a specific sequence with conditional edges |
| LangChain chains (not graph) | No native support for cyclic workflows (re-enter planning after verification failure); StateGraph is the correct abstraction |
| PostgreSQL | Overkill for local single-user SQLite workload; adds Docker container complexity |
| Redis for real-time | Adds infrastructure complexity; FastAPI WebSockets native is sufficient for single-user local tool |
| Redux for state management | Too much boilerplate for a dashboard this size; Zustand achieves the same with 10% of the code |
| Kubernetes | Completely inappropriate scale for a local simulation; Docker Compose is correct |
| Next.js instead of Vite | SSR is unnecessary overhead; Vite starts faster and has simpler configuration |
| Prometheus + Grafana | Real monitoring stack would eclipse the project's actual point (the agents); psutil simulation keeps focus on the right thing |
| Angular / Vue | React was chosen for ecosystem familiarity and component library availability; no strong reason to deviate |

## Critical Design Decisions

| Decision | Chosen Direction | Rationale |
|----------|-----------------|-----------|
| Agent output format | Structured JSON with Pydantic schemas, not freeform text | Qwen 2.5 3B is unreliable at freeform reasoning; structured output with enum selection is predictable |
| Recovery strategy representation | Predefined enum (`RestartService`, `RestoreBackup`, `IsolateContainer`, `RerouteTraffic`, `FullRestart`) | Prevents LLM hallucination of non-existent strategies; keeps the Planning Agent's job to classification |
| Agent communication | Shared LangGraph `RecoveryState` TypedDict passed through the graph | Avoids message-passing complexity; all agents read and write to the same typed state |
| Demo mode | `--mock` flag replaces Ollama calls with deterministic fast responses | Prevents 3-minute demo waits; lets the dashboard and agent flow be validated independently of LLM performance |
| Infrastructure simulation fidelity | Docker containers killed/paused to simulate failures, not process signals or iptables rules | Simple, reliable, visually understandable; sufficient to demonstrate the concept |
