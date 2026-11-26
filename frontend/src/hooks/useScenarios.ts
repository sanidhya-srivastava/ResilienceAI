import { useEffect, useState } from "react";
import { api } from "../api";
import type { ScenarioInfo } from "../types";

const FALLBACK_MVP_SCENARIO: ScenarioInfo = {
  name: "server_crash",
  description:
    "Stops the web-server container, simulating an unexpected process crash. The /health endpoint becomes unreachable until restarted.",
  affected_services: ["resilience-web-server"],
  severity: "critical",
};

export function useScenarios() {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([FALLBACK_MVP_SCENARIO]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .fetchScenarios()
      .then((live) => {
        if (!active || live.length === 0) return;
        setScenarios(live);
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
