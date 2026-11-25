import { useEffect, useState } from "react";
import { api } from "../api";
import type { ScenarioInfo } from "../types";

const PHASE2_LOCKED_SCENARIOS: ScenarioInfo[] = [
  {
    name: "oom_kill",
    description: "Simulates sudden memory exhaustion causing an OOM kill on application containers.",
    affected_services: ["resilience-web-server"],
    severity: "high",
    locked: true,
  },
  {
    name: "database_connection_lost",
    description: "Drops Postgres availability so downstream services lose database connectivity.",
    affected_services: ["resilience-database", "resilience-web-server"],
    severity: "critical",
    locked: true,
  },
  {
    name: "disk_full",
    description: "Fills container scratch storage past 95% capacity, blocking log and temp writes.",
    affected_services: ["resilience-backup-store"],
    severity: "medium",
    locked: true,
  },
];

const FALLBACK_MVP_SCENARIO: ScenarioInfo = {
  name: "server_crash",
  description:
    "Stops the web-server container, simulating an unexpected process crash. The /health endpoint becomes unreachable until restarted.",
  affected_services: ["resilience-web-server"],
  severity: "critical",
};

export function useScenarios() {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([
    FALLBACK_MVP_SCENARIO,
    ...PHASE2_LOCKED_SCENARIOS,
  ]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .fetchScenarios()
      .then((live) => {
        if (!active) return;
        const liveNames = new Set(live.map((s) => s.name));
        const locked = PHASE2_LOCKED_SCENARIOS.filter((s) => !liveNames.has(s.name));
        setScenarios([...live, ...locked]);
      })
      .catch(() => {
        // Keep fallback list if backend is not yet reachable
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return { scenarios, loading };
}
