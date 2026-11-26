import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App";
import { api } from "../src/api";
import { AgentFeed } from "../src/components/AgentFeed";
import { MetricsPanel } from "../src/components/MetricsPanel";
import { ScenarioSelector } from "../src/components/ScenarioSelector";
import { useStore } from "../src/store";

describe("ResilienceAI Dashboard Store & Components", () => {
  beforeEach(() => {
    useStore.getState().reset();
    vi.restoreAllMocks();
    vi.spyOn(api, "fetchScenarios").mockResolvedValue([
      {
        name: "server_crash",
        description: "Stops the web-server container.",
        affected_services: ["resilience-web-server"],
        severity: "critical",
      },
    ]);
    vi.spyOn(api, "fetchIncidents").mockResolvedValue([]);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts in idle state with 5 pending agents", () => {
    const state = useStore.getState();
    expect(state.status).toBe("idle");
    expect(state.agents).toHaveLength(5);
    expect(state.agents.every((a) => a.status === "pending")).toBe(true);
  });

  it("renders agent status icons with accessible aria-labels", () => {
    render(<AgentFeed />);
    for (const name of ["monitor", "diagnose", "plan", "recover", "verify"]) {
      expect(screen.getByLabelText(`${name} agent: pending`)).toBeInTheDocument();
    }
  });

  it("triggers disaster and updates store state on success", async () => {
    vi.spyOn(api, "triggerDisaster").mockResolvedValue({
      incident_id: "inc-ui-001",
      status: "triggered",
      triggered_at: "2026-11-25T10:00:00Z",
    });

    render(<ScenarioSelector />);
    const button = screen.getByRole("button", { name: /Trigger Disaster/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(useStore.getState().incidentId).toBe("inc-ui-001");
      expect(useStore.getState().status).toBe("running");
      expect(useStore.getState().isTriggeringDisaster).toBe(false);
    });
  });

  it("displays and dismisses ErrorBanner when trigger fails", async () => {
    vi.spyOn(api, "triggerDisaster").mockRejectedValue(
      new Error("An incident recovery is already in progress.")
    );

    render(<ScenarioSelector />);
    fireEvent.click(screen.getByRole("button", { name: /Trigger Disaster/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("An incident recovery is already in progress.");

    fireEvent.click(screen.getByRole("button", { name: /Dismiss error/i }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(useStore.getState().triggerError).toBeNull();
  });

  it("hides MetricsPanel while idle and shows it after incident_complete", () => {
    const { rerender } = render(<MetricsPanel />);
    expect(screen.queryByText(/Recovery Analytics/i)).not.toBeInTheDocument();

    act(() => {
      useStore.getState().handleWsMessage({
        type: "agent_update",
        incident_id: "inc-ui-002",
        agent: "monitor",
        state: { anomaly_description: "web-server unreachable" },
        timestamp: "2026-11-25T10:00:01Z",
      });
    });
    expect(
      useStore.getState().agents.find((a) => a.name === "monitor")?.status
    ).toBe("complete");

    act(() => {
      useStore.getState().handleWsMessage({
        type: "incident_complete",
        incident_id: "inc-ui-002",
        success: true,
        metrics: {
          incident_id: "inc-ui-002",
          mttr_seconds: 1.25,
          detection_time_seconds: 0.2,
          diagnosis_time_seconds: 0.3,
          planning_time_seconds: 0.2,
          recovery_time_seconds: 0.4,
          verification_time_seconds: 0.15,
          replan_count: 0,
          recovery_strategy: "restart_container",
          success: true,
        },
      });
    });

    rerender(<MetricsPanel />);
    expect(screen.getByText(/Recovery Succeeded/i)).toBeInTheDocument();
    expect(screen.getByText(/1.250s/i)).toBeInTheDocument();
  });

  it("opens IncidentDetail modal when clicking a recent incident row and closes it", async () => {
    vi.stubGlobal(
      "WebSocket",
      class MockWebSocket {
        close() {}
      }
    );

    vi.spyOn(api, "fetchIncidents").mockResolvedValue([
      {
        id: "inc-hist-001",
        scenario: "corrupted_config",
        triggered_at: "2026-11-26T10:00:00Z",
        status: "recovered",
        completed_at: "2026-11-26T10:00:03Z",
        total_duration_seconds: 2.5,
      },
    ]);

    vi.spyOn(api, "fetchIncidentDetail").mockResolvedValue({
      id: "inc-hist-001",
      scenario: "corrupted_config",
      triggered_at: "2026-11-26T10:00:00Z",
      status: "recovered",
      completed_at: "2026-11-26T10:00:03Z",
      total_duration_seconds: 2.5,
      agent_actions: [
        {
          id: 1,
          incident_id: "inc-hist-001",
          agent_name: "monitor",
          action_type: "detect",
          input_summary: "Probed nginx container",
          output_summary: "Detected HTTP 502 error on config reload",
          success: true,
          duration_ms: 120,
          timestamp: "2026-11-26T10:00:01Z",
        },
        {
          id: 2,
          incident_id: "inc-hist-001",
          agent_name: "verify",
          action_type: "verify",
          input_summary: "Checked health endpoint",
          output_summary: "Health checks passed after config rollback",
          success: true,
          duration_ms: 180,
          timestamp: "2026-11-26T10:00:03Z",
        },
      ],
      metrics: {
        incident_id: "inc-hist-001",
        mttr_seconds: 2.5,
        detection_time_seconds: 0.3,
        diagnosis_time_seconds: 0.6,
        planning_time_seconds: 0.4,
        recovery_time_seconds: 0.8,
        verification_time_seconds: 0.4,
        replan_count: 1,
        recovery_strategy: "restore_config",
        success: true,
      },
    });

    render(<App />);

    const rowButton = await screen.findByRole("button", { name: /inc-hist/i });
    fireEvent.click(rowButton);

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Agent Action Log (2)");
    expect(dialog).toHaveTextContent("Detected HTTP 502 error on config reload");
    expect(dialog).toHaveTextContent("restore_config");
    expect(dialog).toHaveTextContent("2.500s");

    fireEvent.click(screen.getByRole("button", { name: /Close incident details/i }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });
});
