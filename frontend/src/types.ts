export type AgentName = "monitor" | "diagnose" | "plan" | "recover" | "verify";

export type AgentRunStatus = "pending" | "running" | "complete" | "failed";

export type IncidentFlowStatus = "idle" | "running" | "complete" | "failed";

export interface ScenarioInfo {
  name: string;
  description: string;
  affected_services: string[];
  severity: string;
  locked?: boolean;
}

export interface AgentStatus {
  name: AgentName;
  status: AgentRunStatus;
  durationMs?: number;
  outputSummary?: string;
  details?: Record<string, unknown>;
}

export interface RecoveryMetrics {
  incident_id: string;
  mttr_seconds: number | null;
  detection_time_seconds: number | null;
  diagnosis_time_seconds: number | null;
  planning_time_seconds: number | null;
  recovery_time_seconds: number | null;
  verification_time_seconds: number | null;
  replan_count: number;
  recovery_strategy: string | null;
  success: boolean;
}

export interface IncidentSummary {
  id: string;
  scenario: string;
  triggered_at: string;
  status: string;
  completed_at: string | null;
  total_duration_seconds: number | null;
}

export interface TriggerDisasterResponse {
  incident_id: string;
  status: string;
  triggered_at: string;
}

export interface AgentUpdateMessage {
  type: "agent_update";
  incident_id: string;
  agent: AgentName;
  state: Record<string, unknown>;
  timestamp: string;
}

export interface IncidentCompleteMessage {
  type: "incident_complete";
  incident_id: string;
  success: boolean;
  metrics: RecoveryMetrics | null;
  error?: string;
}

export type WsMessage = AgentUpdateMessage | IncidentCompleteMessage;
