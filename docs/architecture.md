# ResilienceAI Architecture

## System Overview

```mermaid
flowchart TB
    UI["React + Vite Dashboard (port 5173)"]
    API["FastAPI Backend (port 8000)"]
    WS["WebSocket /ws/live"]
    DB["SQLite (incidents.db)"]
    LLM["Ollama (Qwen 2.5 7B) / Mock Mode"]

    subgraph LG["LangGraph RecoveryGraph"]
        M["Monitor Agent"] --> D["Diagnose Agent"]
        D --> P["Plan Agent"]
        P --> R["Recover Agent"]
        R --> V["Verify Agent"]
        V -->|replan_required| P
    end

    subgraph INFRA["Docker Compose Simulated Infrastructure"]
        WEB["web-server (nginx:alpine)"]
        PG["app-database (postgres:15)"]
        BK["backup-store (alpine + volume)"]
    end

    UI -->|HTTP POST /disaster/trigger| API
    WS -->|Live Agent Updates| UI
    API --> LG
    API --> DB
    API --> WS
    LG --> LLM
    LG --> INFRA
```

## Component Boundaries

| Component | Responsibility | Does NOT own |
| :--- | :--- | :--- |
| Docker Compose infra | Run simulated services; accept stop/start commands | Disaster logic, agent logic |
| Disaster Simulator | Inject failures via Docker API | Recovery logic |
| LangGraph pipeline | Orchestrate agent execution and state transitions | UI, HTTP routing, DB writes |
| Agents | Perform one step each and return partial `RecoveryState` | Calling the next agent directly |
| FastAPI backend | HTTP routing, WebSocket broadcast, DB persistence | Agent logic, UI rendering |
| React dashboard | Render state and send trigger commands | Business logic |
| SQLite | Persist incident logs, agent actions, and metrics | Nothing else |
