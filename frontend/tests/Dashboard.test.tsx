import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
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
});
