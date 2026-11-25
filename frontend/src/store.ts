import { create } from "zustand";
import { api } from "./api";
import type {
  AgentName,
  AgentStatus,
  AgentUpdateMessage,
  IncidentFlowStatus,
  IncidentSummary,
  RecoveryMetrics,
  WsMessage,
} from "./types";

const AGENT_ORDER: AgentName[] = ["monitor", "diagnose", "plan", "recover", "verify"];

export function createInitialAgents(): AgentStatus[] {
  return AGENT_ORDER.map((name) => ({ name, status: "pending" }));
}

function summarizeAgentOutput(agent: AgentName, state: Record<string, unknown>): string {
  switch (agent) {
    case "monitor": {
      const desc = state.anomaly_description as string | undefined;
      const affected = (state.affected_services as string[] | undefined) ?? [];
      if (desc) return desc;
      return affected.length > 0
        ? `Anomaly detected on: ${affected.join(", ")}`
        : "All monitored services healthy";
    }
    case "diagnose": {
      const cause = (state.root_cause as string | undefined) ?? "unknown";
      const severity = (state.severity as string | undefined) ?? "medium";
      const conf = state.diagnosis_confidence as number | undefined;
      const pct = conf !== undefined ? ` (${Math.round(conf * 100)}% confidence)` : "";
      return `Root cause: ${cause} · severity: ${severity}${pct}`;
    }
    case "plan": {
      const strat = (state.recovery_strategy as string | undefined) ?? "restart_container";
      const rto = state.estimated_rto_seconds as number | undefined;
      return `Strategy: ${strat}${rto ? ` · est. RTO ${rto}s` : ""}`;
    }
    case "recover": {
      const ok = state.recovery_success as boolean | undefined;
      const actions = (state.actions_taken as Array<{ action?: string }> | undefined) ?? [];
      const firstAction = actions[0]?.action ?? "execution complete";
      return ok ? `Executed ${firstAction} successfully` : `Recovery failed during ${firstAction}`;
    }
    case "verify": {
      const passed = state.verification_passed as boolean | undefined;
      const reasoning = state.verdict_reasoning as string | undefined;
      return reasoning ?? (passed ? "Verification passed — services healthy" : "Verification failed");
    }
  }
}

export interface StoreState {
  incidentId: string | null;
  scenario: string | null;
  status: IncidentFlowStatus;
  agents: AgentStatus[];
  metrics: RecoveryMetrics | null;
  triggeredAt: string | null;
  isTriggeringDisaster: boolean;
  triggerError: string | null;
  wsConnected: boolean;
  replanCount: number;
  history: IncidentSummary[];
}

export interface StoreActions {
  triggerDisaster: (scenario: string) => Promise<void>;
  handleAgentUpdate: (update: AgentUpdateMessage) => void;
  handleWsMessage: (msg: WsMessage) => void;
  loadHistory: () => Promise<void>;
  setWsConnected: (connected: boolean) => void;
  dismissError: () => void;
  reset: () => void;
}

const initialState: StoreState = {
  incidentId: null,
  scenario: null,
  status: "idle",
  agents: createInitialAgents(),
  metrics: null,
  triggeredAt: null,
  isTriggeringDisaster: false,
  triggerError: null,
  wsConnected: false,
  replanCount: 0,
  history: [],
};

export const useStore = create<StoreState & StoreActions>((set, get) => ({
  ...initialState,

  triggerDisaster: async (scenario: string) => {
    set({
      isTriggeringDisaster: true,
      triggerError: null,
      metrics: null,
      replanCount: 0,
      agents: createInitialAgents().map((a, idx) =>
        idx === 0 ? { ...a, status: "running" } : a
      ),
    });

    try {
      const response = await api.triggerDisaster(scenario);
      set({
        incidentId: response.incident_id,
        scenario,
        triggeredAt: response.triggered_at,
        status: "running",
        isTriggeringDisaster: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to trigger disaster";
      set({
        isTriggeringDisaster: false,
        triggerError: message,
        status: "idle",
        agents: createInitialAgents(),
      });
    }
  },

  handleAgentUpdate: (update: AgentUpdateMessage) => {
    set((state) => {
      const completedIdx = AGENT_ORDER.indexOf(update.agent);
      const summary = summarizeAgentOutput(update.agent, update.state);
      const replanRequired = Boolean(update.state.replan_required);
      const nextReplanCount =
        typeof update.state.replan_count === "number"
          ? update.state.replan_count
          : state.replanCount;

      const updatedAgents = state.agents.map((a, idx) => {
        if (a.name === update.agent) {
          const failedVerify = update.agent === "verify" && update.state.verification_passed === false;
          return {
            ...a,
            status: failedVerify ? ("failed" as const) : ("complete" as const),
            outputSummary: summary,
            details: update.state,
          };
        }
        // When verify triggers a replan, plan becomes active next
        if (replanRequired && a.name === "plan") {
          return { ...a, status: "running" as const };
        }
        // Otherwise advance the next pending agent to running
        if (!replanRequired && idx === completedIdx + 1 && a.status === "pending") {
          return { ...a, status: "running" as const };
        }
        return a;
      });

      return {
        agents: updatedAgents,
        replanCount: nextReplanCount,
      };
    });
  },

  handleWsMessage: (msg: WsMessage) => {
    if (msg.type === "agent_update") {
      get().handleAgentUpdate(msg);
      return;
    }

    if (msg.type === "incident_complete") {
      set((state) => ({
        status: msg.success ? "complete" : "failed",
        metrics: msg.metrics,
        triggerError: msg.error ?? state.triggerError,
        agents: state.agents.map((a) =>
          a.status === "running"
            ? { ...a, status: msg.success ? "complete" : "failed" }
            : a
        ),
      }));
      void get().loadHistory();
    }
  },

  loadHistory: async () => {
    try {
      const history = await api.fetchIncidents();
      set({ history });
    } catch {
      // Non-fatal in UI
    }
  },

  setWsConnected: (connected: boolean) => set({ wsConnected: connected }),

  dismissError: () => set({ triggerError: null }),

  reset: () =>
    set((state) => ({
      ...initialState,
      agents: createInitialAgents(),
      wsConnected: state.wsConnected,
      history: state.history,
    })),
}));
