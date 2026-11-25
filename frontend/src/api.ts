import type {
  IncidentSummary,
  RecoveryMetrics,
  ScenarioInfo,
  TriggerDisasterResponse,
  WsMessage,
} from "./types";

const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

const WS_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ?? "ws://localhost:8000/ws/live";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Ignore JSON parse errors on non-JSON responses
    }
    throw new Error(detail);
  }

  return (await res.json()) as T;
}

export const api = {
  fetchScenarios: () => request<ScenarioInfo[]>("/disaster/scenarios"),
  triggerDisaster: (scenario: string) =>
    request<TriggerDisasterResponse>("/disaster/trigger", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),
  fetchIncidents: () => request<IncidentSummary[]>("/incidents"),
  fetchMetrics: (incidentId: string) =>
    request<RecoveryMetrics>(`/incidents/${incidentId}/metrics`),
};

export function connectLiveSocket(
  onMessage: (msg: WsMessage) => void,
  onStatusChange?: (connected: boolean) => void
): () => void {
  let socket: WebSocket | null = null;
  let closedByCaller = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let retryDelayMs = 1000;

  const connect = () => {
    if (closedByCaller) return;
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      retryDelayMs = 1000;
      onStatusChange?.(true);
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data as string) as WsMessage;
        onMessage(parsed);
      } catch {
        // Ignore malformed frames
      }
    };

    socket.onclose = () => {
      onStatusChange?.(false);
      if (!closedByCaller) {
        reconnectTimer = setTimeout(() => {
          retryDelayMs = Math.min(retryDelayMs * 2, 10000);
          connect();
        }, retryDelayMs);
      }
    };

    socket.onerror = () => {
      socket?.close();
    };
  };

  connect();

  return () => {
    closedByCaller = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    socket?.close();
  };
}
