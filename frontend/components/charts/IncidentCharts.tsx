"use client";

import type { IncidentSummary } from "@/types/incidents";

type IncidentChartsProps = {
  summary: IncidentSummary | null;
};

export function IncidentCharts({ summary }: IncidentChartsProps) {
  if (!summary) {
    return (
      <section className="rounded-lg border border-line bg-white p-4" aria-label="Incident analytics charts">
        <h2 className="text-lg font-semibold text-ink">Incident analytics</h2>
        <p className="mt-2 text-sm text-muted">Charts will appear after incident summary data loads.</p>
      </section>
    );
  }

  const severityData = Object.entries(summary?.bySeverity ?? {}).map(([severity, count]) => ({ severity, count }));
  const statusData = Object.entries(summary?.byStatus ?? {}).map(([status, count]) => ({ status: status.replaceAll("_", " "), count }));

  return (
    <section className="grid gap-4 md:grid-cols-2" aria-label="Incident analytics charts">
      <div className="rounded-lg border border-line bg-white p-4">
        <h2 className="text-lg font-semibold text-ink">Incidents by severity</h2>
        <MiniBarChart data={severityData} labelKey="severity" barClassName="bg-teal-600" />
      </div>
      <div className="rounded-lg border border-line bg-white p-4">
        <h2 className="text-lg font-semibold text-ink">Incidents by status</h2>
        <MiniBarChart data={statusData} labelKey="status" barClassName="bg-amber-600" />
      </div>
    </section>
  );
}

type MiniBarChartProps<T extends string> = {
  data: Array<Record<T, string> & { count: number }>;
  labelKey: T;
  barClassName: string;
};

function MiniBarChart<T extends string>({ data, labelKey, barClassName }: MiniBarChartProps<T>) {
  const maxCount = Math.max(1, ...data.map((item) => item.count));

  return (
    <div className="mt-4 flex min-h-48 flex-col justify-end gap-3" role="list">
      {data.map((item) => {
        const label = item[labelKey];
        const percentage = Math.max(8, Math.round((item.count / maxCount) * 100));

        return (
          <div key={label} className="grid grid-cols-[minmax(5rem,8rem)_1fr_2rem] items-center gap-3 text-sm" role="listitem">
            <span className="truncate text-muted" title={label}>{label}</span>
            <div className="h-3 rounded-full bg-slate-100">
              <div className={`h-3 rounded-full ${barClassName}`} style={{ width: `${percentage}%` }} aria-hidden="true" />
            </div>
            <span className="text-right font-semibold text-ink">{item.count}</span>
          </div>
        );
      })}
    </div>
  );
}
