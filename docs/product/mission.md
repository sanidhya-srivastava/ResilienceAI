# Mission

## One-Sentence Mission

ResilienceAI exists to simulate digital infrastructure disasters and autonomously recover from them, so that developers can demonstrate real multi-agent AI engineering in a visually observable, locally-runnable system.

## Job Story

When I'm applying for AI/agents engineering roles, I struggle to demonstrate I understand multi-agent orchestration beyond chatbots and RAG pipelines, so I currently put generic LLM projects on my portfolio that don't stand out. I'd hire a project that proves I can build a real stateful multi-agent system with observable behaviour in a domain (disaster recovery) that maps to production reliability engineering.

## Why We're Right to Build This

This is a self-taught developer building for portfolio differentiation. The technical advantage is not domain access — it's willingness to integrate a genuinely complex stack (LangGraph + Ollama + Docker Compose + FastAPI + React) in a way that most portfolio projects don't attempt. The DR domain was chosen deliberately: it has real terminology (RTO, RPO, MTTR, backup validation, root cause analysis) that signals depth to technical interviewers, and it maps directly to SRE/platform engineering roles that are in demand.

## Who We Serve

**Primary:** A self-taught developer preparing for employment in AI engineering, ML engineering, or backend/full-stack roles. They want one project that demonstrates systems thinking, not just API calling.

**Secondary (implicit):** The technical interviewer who will evaluate this project — they need to see clean code, a live demo, and evidence of real engineering judgment.

## The Problem We Solve

Most AI portfolio projects are chatbots, RAG pipelines, or fine-tuning experiments. They demonstrate knowledge of APIs, not architecture. Multi-agent orchestration with observable state — where multiple specialised agents hand off work through a typed state graph and a human can watch it happen — is genuinely rare in portfolios and maps directly to what AI-native companies are building in production.

## Why Now

LangGraph hit stable 1.0 in 2024. Ollama made local LLM inference accessible with a single CLI command. Docker Compose makes multi-container infrastructure simulation trivial. All the components needed to build this exist, are free, and run on a developer laptop. This was not true 2 years ago.

## What Success Looks Like (Year 1)

- A live, demo-able system where a user selects a disaster scenario, watches 5–8 agents execute a recovery workflow in real time on a React dashboard, and sees quantitative metrics at the end (MTTR, recovery success rate, agentic vs. rule-based comparison).
- Clean, well-documented GitHub repository that a technical interviewer can clone and run in under 10 minutes.
- At least one job interview where the interviewer specifically asks about this project.
- All five disaster scenarios implemented and passing the evaluation suite.
