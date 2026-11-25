import { useStore } from "../store";
import { MTTRBreakdown } from "./MTTRBreakdown";
import { RecoveryStatus } from "./RecoveryStatus";

export function MetricsPanel() {
  const status = useStore((s) => s.status);
  const metrics = useStore((s) => s.metrics);

  if (status !== "complete" && status !== "failed") return null;

  return (
    <section
      aria-labelledby="metrics-heading"
      className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"
    >
      <h2 id="metrics-heading" className="mb-4 text-lg font-semibold text-slate-100">
        3. Recovery Analytics &amp; MTTR
      </h2>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RecoveryStatus metrics={metrics} success={status === "complete"} />
        {metrics && <MTTRBreakdown metrics={metrics} />}
      </div>
    </section>
  );
}
