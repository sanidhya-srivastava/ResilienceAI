import type { ScenarioInfo } from "../types";

const SEVERITY_BADGES: Record<string, string> = {
  critical: "bg-red-500/15 text-red-300 border-red-500/30",
  high: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  medium: "bg-sky-500/15 text-sky-300 border-sky-500/30",
};

interface ScenarioCardProps {
  scenario: ScenarioInfo;
  isSelected: boolean;
  onSelect: () => void;
}

export function ScenarioCard({ scenario, isSelected, onSelect }: ScenarioCardProps) {
  const locked = Boolean(scenario.locked);
  const badgeStyle =
    SEVERITY_BADGES[scenario.severity] ?? "bg-slate-700/40 text-slate-300 border-slate-600";

  return (
    <button
      type="button"
      disabled={locked}
      onClick={onSelect}
      aria-pressed={isSelected}
      className={`flex flex-col justify-between rounded-xl border p-4 text-left transition-all ${
        locked
          ? "cursor-not-allowed border-slate-800 bg-slate-900/40 opacity-55"
          : isSelected
          ? "border-cyan-400 bg-cyan-950/30 ring-1 ring-cyan-400/50"
          : "border-slate-800 bg-slate-900 hover:border-slate-700 hover:bg-slate-900/90"
      }`}
    >
      <div>
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold text-slate-100 capitalize">
            {scenario.name.replace(/_/g, " ")}
          </h3>
          <span className={`rounded-full border px-2 py-0.5 text-xs font-medium uppercase ${badgeStyle}`}>
            {locked ? "Phase 2" : scenario.severity}
          </span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">{scenario.description}</p>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {scenario.affected_services.map((svc) => (
          <span
            key={svc}
            className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[11px] text-slate-300"
          >
            {svc}
          </span>
        ))}
      </div>
      {locked && (
        <p className="mt-2 text-[11px] font-medium text-slate-500">Coming in Phase 2</p>
      )}
    </button>
  );
}
