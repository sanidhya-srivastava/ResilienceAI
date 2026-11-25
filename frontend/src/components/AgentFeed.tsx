import { useStore } from "../store";
import { AgentCard } from "./AgentCard";

export function AgentFeed() {
  const agents = useStore((s) => s.agents);
  const status = useStore((s) => s.status);
  const replanCount = useStore((s) => s.replanCount);

  return (
    <section aria-labelledby="pipeline-heading" className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 id="pipeline-heading" className="text-lg font-semibold text-slate-100">
            2. Live Agent Pipeline
          </h2>
          <p className="text-xs text-slate-400">
            {status === "idle"
              ? "Waiting for disaster trigger."
              : "Monitor → Diagnose → Plan → Recover → Verify"}
          </p>
        </div>
        {replanCount > 0 && (
          <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-300">
            Replans: {replanCount}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
        {agents.map((agent) => (
          <AgentCard key={agent.name} agent={agent} />
        ))}
      </div>
    </section>
  );
}
