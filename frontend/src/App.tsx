import { useEffect } from "react";
import { connectLiveSocket } from "./api";
import { AgentFeed } from "./components/AgentFeed";
import { MetricsPanel } from "./components/MetricsPanel";
import { ScenarioSelector } from "./components/ScenarioSelector";
import { useStore } from "./store";

export function App() {
  const wsConnected = useStore((s) => s.wsConnected);
  const incidentId = useStore((s) => s.incidentId);
  const history = useStore((s) => s.history);
  const handleWsMessage = useStore((s) => s.handleWsMessage);
  const setWsConnected = useStore((s) => s.setWsConnected);
  const loadHistory = useStore((s) => s.loadHistory);

  useEffect(() => {
    void loadHistory();
    const disconnect = connectLiveSocket(handleWsMessage, setWsConnected);
    return disconnect;
  }, [handleWsMessage, setWsConnected, loadHistory]);

  return (
    <main className="mx-auto min-h-screen max-w-6xl space-y-6 p-6 md:p-8">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">ResilienceAI</h1>
          <p className="mt-1 text-sm text-slate-400">
            Autonomous multi-agent digital disaster recovery simulator
          </p>
        </div>

        <div className="flex items-center gap-3">
          {incidentId && (
            <span className="rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 font-mono text-xs text-slate-300">
              Incident: {incidentId.slice(0, 8)}
            </span>
          )}
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
              wsConnected
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-slate-700 bg-slate-900 text-slate-400"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                wsConnected ? "bg-emerald-400" : "bg-slate-500"
              }`}
            />
            {wsConnected ? "Live Stream Connected" : "Stream Offline"}
          </span>
        </div>
      </header>

      <ScenarioSelector />
      <AgentFeed />
      <MetricsPanel />

      {history.length > 0 && (
        <section
          aria-labelledby="history-heading"
          className="rounded-xl border border-slate-800 bg-slate-900/40 p-5"
        >
          <h2 id="history-heading" className="mb-3 text-sm font-semibold text-slate-200">
            Recent Incidents
          </h2>
          <div className="divide-y divide-slate-800 text-xs">
            {history.slice(0, 5).map((inc) => (
              <div key={inc.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="font-mono text-slate-300">{inc.id.slice(0, 8)}</span>
                <span className="capitalize text-slate-200">{inc.scenario.replace(/_/g, " ")}</span>
                <span
                  className={`rounded px-2 py-0.5 font-medium uppercase ${
                    inc.status === "recovered"
                      ? "bg-emerald-500/15 text-emerald-300"
                      : inc.status === "failed"
                      ? "bg-red-500/15 text-red-300"
                      : "bg-cyan-500/15 text-cyan-300"
                  }`}
                >
                  {inc.status}
                </span>
                <span className="text-slate-400">
                  {inc.total_duration_seconds != null
                    ? `${inc.total_duration_seconds.toFixed(3)}s`
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

export default App;
