import { useState } from "react";
import { useScenarios } from "../hooks/useScenarios";
import { useStore } from "../store";
import { ErrorBanner } from "./ErrorBanner";
import { ScenarioCard } from "./ScenarioCard";

export function ScenarioSelector() {
  const { scenarios } = useScenarios();
  const [selected, setSelected] = useState<string>("server_crash");
  const triggerDisaster = useStore((s) => s.triggerDisaster);
  const status = useStore((s) => s.status);
  const isTriggeringDisaster = useStore((s) => s.isTriggeringDisaster);
  const reset = useStore((s) => s.reset);

  const isRunning = status === "running";
  const buttonDisabled = !selected || isRunning || isTriggeringDisaster;

  return (
    <section aria-labelledby="scenario-heading" className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 id="scenario-heading" className="text-lg font-semibold text-slate-100">
            1. Select Disaster Scenario
          </h2>
          <p className="text-xs text-slate-400">
            Inject a controlled failure and observe autonomous multi-agent recovery.
          </p>
        </div>
        {status !== "idle" && (
          <button
            type="button"
            onClick={reset}
            disabled={isRunning}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 disabled:opacity-40"
          >
            Reset Run
          </button>
        )}
      </div>

      <ErrorBanner />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {scenarios.map((scenario) => (
          <ScenarioCard
            key={scenario.name}
            scenario={scenario}
            isSelected={selected === scenario.name}
            onSelect={() => setSelected(scenario.name)}
          />
        ))}
      </div>

      <div className="mt-4 flex items-center justify-end">
        <button
          type="button"
          onClick={() => selected && void triggerDisaster(selected)}
          disabled={buttonDisabled}
          className="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-red-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {isTriggeringDisaster
            ? "Initiating..."
            : isRunning
            ? "Recovery in progress..."
            : "Trigger Disaster"}
        </button>
      </div>
    </section>
  );
}
