import { useEffect, useState } from "react";
import { api } from "../api";
import type { IncidentDetail as IncidentDetailData } from "../types";
import { MTTRBreakdown } from "./MTTRBreakdown";
import { RecoveryStatus } from "./RecoveryStatus";

function formatTimestamp(ts: string | null): string {
  if (!ts) return "—";
  const parsed = new Date(ts);
  return Number.isNaN(parsed.getTime()) ? ts : parsed.toLocaleString();
}

export function IncidentDetail({
  incidentId,
  onClose,
}: {
  incidentId: string;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<IncidentDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .fetchIncidentDetail(incidentId)
      .then((data) => {
        if (!cancelled) {
          setDetail(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load incident details.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [incidentId]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="incident-detail-title"
        className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 id="incident-detail-title" className="text-xl font-bold capitalize text-white">
              {detail ? detail.scenario.replace(/_/g, " ") : "Incident Details"}
            </h2>
            <p className="mt-1 font-mono text-xs text-slate-400">ID: {incidentId}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close incident details"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
          >
            Close
          </button>
        </div>

        {loading && (
          <div className="py-12 text-center text-sm text-slate-400">
            Loading incident details...
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-red-500/40 bg-red-950/40 p-4 text-sm text-red-200"
          >
            {error}
          </div>
        )}

        {!loading && !error && detail && (
          <div className="mt-5 space-y-6">
            <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-xs sm:grid-cols-4">
              <div>
                <div className="text-slate-400">Status</div>
                <div className="mt-1 font-semibold uppercase text-slate-100">{detail.status}</div>
              </div>
              <div>
                <div className="text-slate-400">Total Duration</div>
                <div className="mt-1 font-mono text-slate-100">
                  {detail.total_duration_seconds != null
                    ? `${detail.total_duration_seconds.toFixed(3)}s`
                    : "—"}
                </div>
              </div>
              <div>
                <div className="text-slate-400">Triggered</div>
                <div className="mt-1 text-slate-200">{formatTimestamp(detail.triggered_at)}</div>
              </div>
              <div>
                <div className="text-slate-400">Completed</div>
                <div className="mt-1 text-slate-200">{formatTimestamp(detail.completed_at)}</div>
              </div>
            </div>

            {detail.metrics ? (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <RecoveryStatus metrics={detail.metrics} success={detail.metrics.success} />
                <MTTRBreakdown metrics={detail.metrics} />
              </div>
            ) : (
              <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-xs text-slate-400">
                No quantitative recovery metrics recorded for this incident.
              </div>
            )}

            <div>
              <h3 className="mb-3 text-sm font-semibold text-slate-200">
                Agent Action Log ({detail.agent_actions.length})
              </h3>
              {detail.agent_actions.length === 0 ? (
                <p className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-xs text-slate-400">
                  No agent actions recorded for this incident.
                </p>
              ) : (
                <ol className="space-y-2.5">
                  {detail.agent_actions.map((action, index) => (
                    <li
                      key={action.id ?? `${action.agent_name}-${action.timestamp}-${index}`}
                      className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 text-xs"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 font-mono text-[11px] text-slate-300">
                            {index + 1}
                          </span>
                          <span className="font-semibold capitalize text-slate-100">
                            {action.agent_name} Agent
                          </span>
                          <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-slate-300">
                            {action.action_type}
                          </span>
                          <span
                            className={`rounded px-2 py-0.5 text-[11px] font-medium uppercase ${
                              action.success
                                ? "bg-emerald-500/15 text-emerald-300"
                                : "bg-red-500/15 text-red-300"
                            }`}
                          >
                            {action.success ? "pass" : "fail"}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
                          {action.duration_ms != null && <span>{action.duration_ms}ms</span>}
                          <span>{formatTimestamp(action.timestamp)}</span>
                        </div>
                      </div>

                      {action.input_summary && (
                        <p className="mt-2 text-slate-400">
                          <span className="font-medium text-slate-300">Input:</span>{" "}
                          {action.input_summary}
                        </p>
                      )}
                      {action.output_summary && (
                        <p className="mt-1 text-slate-200">
                          <span className="font-medium text-slate-300">Output:</span>{" "}
                          {action.output_summary}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
