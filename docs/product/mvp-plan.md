# MVP Plan

## Core Value Proposition

A complete, working end-to-end multi-agent disaster recovery loop — trigger a server crash, watch five specialised agents detect, diagnose, plan, recover, and verify the restoration in real time on a live dashboard — running entirely on a local machine at zero cost.

## MVP Scope

### Must Have (MVP gates on these)

- Dockerised simulated infrastructure: at least one "server" container, one "database" container, one "backup" container
- Disaster Simulator that can inject a **server crash** (the first scenario) via a REST endpoint or CLI command
- Five-agent LangGraph pipeline: Monitor → Diagnose → Plan → Recover → Verify
- Agents powered by Ollama + Qwen 2.5 3B with structured output schemas (no freeform generation)
- FastAPI backend exposing: trigger disaster, get agent status, get recovery metrics
- React + Vite dashboard showing: live agent state, recovery progress, final metrics (MTTR, success/fail)
- SQLite persistence: incident log, agent actions, recovery timeline
- End-to-end demo: from disaster trigger to "Recovery verified" in a single continuous flow

### Explicitly Out of MVP

- Remaining four disaster scenarios (database corruption, ransomware, network outage, cloud region failure) — added in Phase 2
- Agentic vs. rule-based comparison — added in Phase 3 (requires a rule-based baseline to compare against)
- Backup Agent as a separate agent — MVP merges backup discovery into the Recovery Agent; extract as standalone in Phase 2
- Advanced UI features: incident history browser, multi-scenario comparison view, PDF report export
- Authentication, user management, or multi-user support
- Production deployment, cloud hosting, or external infrastructure integration

## Go-to-Market Approach

This is a portfolio project, not a commercial product. "Go-to-market" means GitHub discoverability and interview readiness:
1. Push to public GitHub with a README that includes a 1-minute GIF/video of the demo, a clean `docker-compose up` quickstart, and a link to the architecture diagram.
2. Write one technical blog post on dev.to or Medium: "I built a multi-agent disaster recovery simulator with LangGraph and Ollama — here's what I learned." This surfaces the project to relevant search traffic.

## What We'll Do Manually (Pre-Scale)

- Disaster injection: MVP uses a manual API call or button press to trigger disasters — no autonomous probabilistic failure injection yet
- Recovery strategy selection: MVP pre-defines recovery strategies as a small enum; the Planning Agent selects from options, it does not generate novel strategies
- Backup state: MVP uses a static Docker volume as a "backup" rather than a real incremental backup system
- Performance metrics: MVP computes MTTR from timestamps, not from a real monitoring stack

## Success Metrics

| Metric | Target | Timeframe |
|--------|--------|-----------|
| End-to-end recovery demo working | Server crash → verified recovery in one run | MVP complete |
| Agent pipeline latency | Full loop completes in < 3 minutes on local hardware | MVP complete |
| GitHub clone + run time | `docker-compose up` → working dashboard in < 10 minutes | MVP complete |
| Code coverage (critical paths) | Agent state transitions and tool calls have unit tests | MVP complete |
| Dashboard completeness | Live agent status + metrics visible during and after recovery | MVP complete |

## Biggest Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Qwen 2.5 3B fails at structured JSON output | High | High | Use Ollama structured outputs / JSON mode; design agents to pick from enum options, not generate freeform text |
| Local inference too slow for live demo | Medium | High | Add `--mock` mode where agents use fast deterministic responses; use real mode for evaluation, mock mode for demos |
| Docker container lifecycle complexity | Medium | Medium | Use simple health-check scripts, not full orchestration; keep simulated infra minimal |
| LangGraph state schema becomes unwieldy | Medium | Medium | Define one `RecoveryState` TypedDict up front; never add fields mid-implementation without updating all agents |
| Scope creep during implementation | High | Medium | Strictly enforce MVP scope; log all "nice to have" ideas to a `docs/backlog.md` file and do not implement until Phase 1 is demo-able |
