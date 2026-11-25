import type { RecoveryMetrics } from "../types";

export function RecoveryStatus({
  metrics,
  success,
}: {
  metrics: RecoveryMetrics | null;
  success: boolean;
}) {
  const mttrLabel =
    metrics?.mttr_seconds != null
      ? `${metrics.mttr_seconds.toFixed(3)}s`
      : "—";

  return (
    <div
      className={`rounded-lg border p-4 ${
        success
          ? "border-emerald-500/40 bg-emerald-950/30"
          : "border-red-500/40 bg-red-950/30"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <span
            className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${
              success
                ? "bg-emerald-500/20 text-emerald-300"
                : "bg-red-500/20 text-red-300"
            }`}
          >
            {success ? "Recovery Succeeded" : "Recovery Failed"}
          </span>
          <p className="mt-2 text-xs text-slate-300">
            Strategy:{" "}
            <span className="font-mono text-slate-100">
              {metrics?.recovery_strategy ?? "unknown"}
            </span>
          </p>
        </div>

        <div className="flex gap-6 text-right">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400">MTTR</div>
            <div className="text-2xl font-bold text-slate-100">{mttrLabel}</div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400">Replans</div>
            <div className="text-2xl font-bold text-slate-100">
              {metrics?.replan_count ?? 0}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
