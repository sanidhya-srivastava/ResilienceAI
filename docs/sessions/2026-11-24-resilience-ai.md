# Session Q&A Log: ResilienceAI

**Date:** 2026-11-24  
**Mode:** New Product  
**Scope:** Deep  
**Phases completed:** 0, 1, 2, 3, 4, 5, 7  
**Outcome:** Full product documents (mission, MVP plan, roadmap, tech stack) + complete implementation plan (15 units across 6 weeks) produced. SCOPE REDUCTION review applied.

---

## Questions & Answers by Phase

### Phase 0: Intake & Route

**Q:** Mode detection (internal). No existing code in directory. Input describes building from scratch.  
**User:** N/A — auto-detected.  
**AI position:** New Product mode. Deep scope (7-phase plan, 8 agents, explicit tech stack).  
**Resolved:** New Product / Deep scope confirmed.

---

### Phase 2: Challenge & Explore

**Q:** What's your background or context for this project?  
**User:** Self-taught / hobbyist — building this to demonstrate skills for employment.  
**AI position:** Legitimate foundation. Risk is complexity masking employability — a project that's impressive but un-demo-able does no good. The employment framing must drive every scope decision.  
**Resolved:** Portfolio differentiation is the primary goal. Hirability beats technical completeness.

---

**Q:** What job role is this project primarily meant to demonstrate?  
**User:** Generalised portfolio — I want something impressive that works across role types.  
**AI position:** Pushed back. "Generalised" is a known failure pattern for portfolio projects. Hiring managers remember one thing. The primary wow moment for ResilienceAI should be the live dashboard showing agents recovering in real time — that is what gets screenshotted and remembered.  
**Resolved:** Generalised architecture is acceptable, but the demo must have one clear, memorable moment.

---

**Q:** What do most AI portfolio projects look like right now?  
**User:** Genuinely nothing that shows multi-agent orchestration — that's a real gap I'm trying to fill.  
**AI position:** Confirmed correct. Multi-agent orchestration with observable state in a domain-specific context is rare. The employment thesis is validated.  
**Resolved:** ResilienceAI's differentiation is real. Proceeding.

---

**Q:** What's the smallest version of ResilienceAI that would genuinely impress a hiring manager?  
**User:** A working multi-agent loop (monitor → diagnose → plan → recover → verify) with one disaster type, then expand.  
**AI position:** Excellent answer. This is the right wedge. One working end-to-end loop is infinitely more impressive than 8 partial agents. Plan-as-written (all 5 scenarios simultaneously) is too wide for MVP.  
**Resolved:** MVP = one scenario (server crash) + complete 5-agent loop + live dashboard. All other scenarios deferred to Phase 2.

---

**Q:** How far along is the implementation?  
**User:** No, this is greenfield — I haven't written any code yet.  
**AI position:** Good — no sunk costs. Can design correctly from the start.  
**Resolved:** Greenfield confirmed. Start from Unit 1.

---

### Phase 5: Validate

**Q:** Review scope mode selection.  
**User:** SCOPE REDUCTION — find the minimum version that still impresses in an interview.  
**AI position:** Committed to SCOPE REDUCTION throughout. Applied consistently.  
**Resolved:** SCOPE REDUCTION mode applied. Units 13+14+15 merged. Doc scope cut. `docker-compose.override.yml` removed.

---

## Key Decisions

| Decision | Chosen | Phase | Rationale |
|----------|--------|-------|-----------|
| MVP scenario count | 1 (server crash only) | 2 | One working loop is more impressive than 5 partial ones |
| Agent output format | Structured JSON with Pydantic enums | 3 | Qwen 2.5 3B unreliable at freeform; enums prevent hallucination |
| Recovery strategies | Predefined enum catalog | 3 | Planning Agent selects from options, does not generate novel strategies |
| Mock mode | `MOCK_MODE=true` env var, `mock_responses.py` fixture | 4/5 | Demo without 3-minute Ollama wait; critical first-class deliverable |
| Backup Agent | Merged into Recover Agent for MVP | 4 | Extracted as standalone in Phase 2; reduces complexity without losing concept |
| Frontend state | Single Zustand store (not two) | 5 (reduction) | Avoids unnecessary abstraction for a solo dev building a local tool |
| Dashboard units | Merged 3 UI units into 1 | 5 (reduction) | Same files, one implementation pass; reduces coordination overhead |
| Documentation scope | README + running-locally.md + CI only | 5 (reduction) | Arch deep-dive deferred to Phase 3; interview-critical docs only |

---

## Positions Where AI Pushed Back

| Topic | AI Position | User Response | Final Resolution |
|-------|------------|---------------|------------------|
| "Generalised portfolio" goal | A project that tries to prove everything proves nothing — pick one wow moment | User noted the generalised goal | Accepted: architecture stays broad, but demo must have one clear memorable moment |
| Plan-as-written (7 phases, 8 agents, 5 scenarios simultaneously for MVP) | Too wide for MVP; build depth before breadth | User chose the right wedge themselves (one loop, one scenario) | MVP scoped to server crash + 5-agent loop |
| Q6 future-fit | Agentic AI is not a fad, but "just LangGraph" becomes generic by 2026; domain depth and observable system are the differentiators | N/A (not disputed) | Plan emphasises DR terminology and live observable state as differentiators |
