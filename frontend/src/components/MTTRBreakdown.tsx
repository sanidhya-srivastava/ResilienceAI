import {
  Bar,
  BarChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RecoveryMetrics } from "../types";

const PHASE_COLORS = {
  detection: "#3b82f6",
  diagnosis: "#8b5cf6",
  planning: "#f59e0b",
  recovery: "#ef4444",
  verification: "#10b981",
};

export function MTTRBreakdown({ metrics }: { metrics: RecoveryMetrics }) {
  const toMs = (sec: number | null) => Math.round((sec ?? 0) * 1000 * 100) / 100;

  const data = [
    {
      name: "Pipeline",
      detection: toMs(metrics.detection_time_seconds),
      diagnosis: toMs(metrics.diagnosis_time_seconds),
      planning: toMs(metrics.planning_time_seconds),
      recovery: toMs(metrics.recovery_time_seconds),
      verification: toMs(metrics.verification_time_seconds),
    },
  ];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-200">
        Phase Duration Breakdown (ms)
      </h3>
      <div className="h-36 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
            <XAxis type="number" stroke="#94a3b8" fontSize={12} unit="ms" />
            <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={12} width={60} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                borderColor: "#334155",
                color: "#f8fafc",
                fontSize: "12px",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "12px" }} />
            <Bar dataKey="detection" stackId="a" fill={PHASE_COLORS.detection} name="Monitor" />
            <Bar dataKey="diagnosis" stackId="a" fill={PHASE_COLORS.diagnosis} name="Diagnose" />
            <Bar dataKey="planning" stackId="a" fill={PHASE_COLORS.planning} name="Plan" />
            <Bar dataKey="recovery" stackId="a" fill={PHASE_COLORS.recovery} name="Recover" />
            <Bar dataKey="verification" stackId="a" fill={PHASE_COLORS.verification} name="Verify" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
