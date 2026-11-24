# Roadmap

## Phase 1: Prove It Works (MVP)
**Hypothesis:** A multi-agent LangGraph pipeline can detect, diagnose, plan, and recover from a simulated server crash on local infrastructure, and the result is demo-able in a 20-minute interview.

**We'll know it's true when:** A complete end-to-end recovery run (disaster trigger → agent loop → verified recovery) completes on a fresh `docker-compose up` without manual intervention, and the React dashboard shows the full timeline.

**Goal:** One working scenario (server crash), five agents, live dashboard, clean GitHub repo.

**Deliverables:**
- Dockerised simulated infrastructure (server, database, backup containers)
- Disaster Simulator with server crash injection
- LangGraph pipeline: Monitor → Diagnose → Plan → Recover → Verify
- FastAPI backend with disaster trigger and status endpoints
- React + Vite dashboard: live agent state + recovery metrics
- SQLite incident and action log
- Unit tests for agent state transitions and tool calls
- README with quickstart, architecture diagram, and demo GIF/video

**Exit criteria:**
- Full recovery loop runs end-to-end without crashing or hanging
- Dashboard correctly shows agent state transitions in real time
- All unit tests pass
- `docker-compose up` works on a clean machine (verified on at least one other machine or CI)

---

## Phase 2: Make It Repeatable (All 5 Scenarios)
**Hypothesis:** The agent architecture generalises across different disaster types with per-scenario configuration, not per-scenario code rewrites.

**We'll know it's true when:** All five disaster scenarios complete end-to-end using the same LangGraph pipeline with scenario-specific tool implementations, and each has its own incident report in the dashboard.

**Goal:** Expand from one scenario to all five. Add the Backup Agent as a standalone component. Add incident history to the dashboard.

**Deliverables:**
- Disaster Simulator scenarios: database corruption, ransomware simulation, network outage, cloud region failure simulation
- Backup Agent extracted from Recovery Agent as a dedicated graph node
- Per-scenario tool implementations for each agent
- Dashboard: incident history browser, scenario selector with descriptions
- Scenario configuration file (`scenarios.yaml`) — adding a scenario should not require code changes to the core pipeline
- Expanded test suite: at least 3 test scenarios per agent per disaster type

**Exit criteria:**
- All 5 disaster scenarios complete end-to-end
- Backup Agent is standalone and properly sequenced in the graph
- Each scenario generates a distinct, accurate incident report
- Scenario config is data-driven (no hardcoded scenario logic in agent code)

---

## Phase 3: Scale It (Evaluation and Comparison)
**Hypothesis:** The agentic recovery system measurably outperforms a rule-based baseline on at least two of the five disaster scenarios, and this difference is visible in the dashboard.

**We'll know it's true when:** The comparison view in the dashboard shows side-by-side MTTR, recovery steps, and success rates for agentic vs. rule-based, with statistically meaningful differences on at least two scenarios.

**Goal:** Add rule-based recovery baseline, comparison analytics, PDF report export, and final documentation.

**Deliverables:**
- Rule-based recovery system: deterministic scripts for each disaster type (the "before AI" baseline)
- Comparison mode: run the same scenario through both systems, compare outcomes
- Analytics dashboard: MTTR comparison, step count, success rate, recovery timeline overlay
- PDF/JSON report export
- Full documentation: architecture deep-dive, design decisions, lessons learned
- Final README polish: architecture diagrams (Mermaid), API reference, evaluation results

**Exit criteria:**
- Side-by-side comparison works for all 5 scenarios
- Report export produces a clean, readable document
- Documentation is complete enough for a cold reader to understand the system
- Repository is interview-ready: code quality, comments, tests, CI

---

## Deferred (Backlog)

| Item | Reason deferred |
|------|----------------|
| Autonomous probabilistic failure injection (failures happen on a schedule) | Adds complexity without adding demo value; manual injection is clearer for interviews |
| Multi-node simulated infrastructure (10+ containers) | Diminishing returns on demo value; one server + one DB + one backup is sufficient to show the concept |
| Real LLM-generated recovery runbooks | Requires a larger model; Qwen 2.5 3B is insufficient for reliable freeform generation |
| Cloud deployment (hosted demo) | Out of scope for a local-first, cost-zero project; adds infra complexity |
| Authentication and multi-user support | Portfolio projects don't need auth; adds code complexity without demonstrating relevant skills |
| Integration with real monitoring tools (Prometheus, Grafana) | Interesting but not necessary for the demo; psutil simulation is sufficient |
| Streaming LLM output to dashboard | Nice UX, significant complexity; deferred unless Phase 1 finishes early |
