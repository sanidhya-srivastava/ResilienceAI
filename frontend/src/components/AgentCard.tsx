import type { AgentRunStatus, AgentStatus } from "../types";

const STATUS_STYLES: Record<AgentRunStatus, string> = {
  pending: "border-slate-800 bg-slate-900/50 text-slate-400",
  running: "border-cyan-500/60 bg-cyan-950/30 text-cyan-100 animate-pulse",
  complete: "border-emerald-500/50 bg-emerald-950/25 text-emerald-100",
  failed: "border-red-500/60 bg-red-950/30 text-red-100",
};

const STATUS_ICONS: Record<AgentRunStatus, string> = {
  pending: "○",
  running: "◉",
  complete: "✓",
  failed: "✕",
};

const AGENT_DESCRIPTIONS: Record<AgentStatus["name"], string> = {
  monitor: "Polls service health endpoints & detects anomalies",
  diagnose: "Classifies root cause and incident severity via LLM",
  plan: "Selects optimal recovery playbook from strategy catalog",
  recover: "Executes deterministic Docker & backup remediation",
  verify: "Re-checks health and decides pass or replan loop",
};

export function AgentCard({ agent }: { agent: AgentStatus }) {
  return (
    <div className={`rounded-xl border p-4 transition-all ${STATUS_STYLES[agent.status]}`}>
      <div className="flex items-center gap-2.5">
        <span
          aria-label={`${agent.name} agent: ${agent.status}`}
          className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-950/60 text-sm font-bold"
        >
          {STATUS_ICONS[agent.status]}
        </span>
        <h3 className="font-semibold capitalize text-slate-100">{agent.name} Agent</h3>
        <span className="ml-auto rounded bg-slate-950/60 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-300">
          {agent.status}
        </span>
      </div>

      <p className="mt-2 text-xs text-slate-300/90">
        {agent.outputSummary ?? AGENT_DESCRIPTIONS[agent.name]}
      </p>
    </div>
  );
}
