"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchIncidents, fetchIncidentSummary } from "@/lib/api";
import { useRefresh } from "@/context/RefreshContext";
import { IncidentCharts } from "@/components/charts/IncidentCharts";
import { BarChart3, TrendingUp, Award, Calendar } from "lucide-react";
import type { Incident, IncidentSummary } from "@/types/incidents";

export default function AnalyticsPage() {
  const { refreshTrigger } = useRefresh();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [incList, sumData] = await Promise.all([
          fetchIncidents(),
          fetchIncidentSummary()
        ]);
        setIncidents(incList);
        setSummary(sumData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [refreshTrigger]);

  const activeIncidents = useMemo(() => incidents.filter((incident) => !["RESOLVED", "CANCELLED"].includes(incident.status)).length, [incidents]);
  const avgSeverity = useMemo(() => {
    if (incidents.length === 0) return 0;
    return (incidents.reduce((sum, i) => sum + i.severity, 0) / incidents.length).toFixed(1);
  }, [incidents]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-ink">Smart City Analytics Center</h2>
        <p className="text-sm text-muted">Identify trends, resolve bottlenecks, and monitor severity distribution patterns.</p>
      </div>

      {/* Metric Cards */}
      <section className="grid gap-4 md:grid-cols-4">
        <div className="bg-white rounded-xl border border-line p-5 shadow-sm">
          <span className="text-xs font-bold text-muted uppercase">Total Reported</span>
          <p className="text-2xl font-bold text-ink mt-1">{incidents.length}</p>
        </div>
        <div className="bg-white rounded-xl border border-line p-5 shadow-sm">
          <span className="text-xs font-bold text-muted uppercase">Active Queue</span>
          <p className="text-2xl font-bold text-ink mt-1">{activeIncidents}</p>
        </div>
        <div className="bg-white rounded-xl border border-line p-5 shadow-sm">
          <span className="text-xs font-bold text-muted uppercase">Average Severity</span>
          <p className="text-2xl font-bold text-ink mt-1">{avgSeverity} / 5.0</p>
        </div>
        <div className="bg-white rounded-xl border border-line p-5 shadow-sm">
          <span className="text-xs font-bold text-muted uppercase">Resolution Rate</span>
          <p className="text-2xl font-bold text-ink mt-1">
            {incidents.length > 0
              ? `${Math.round(((incidents.length - activeIncidents) / incidents.length) * 100)}%`
              : "0%"}
          </p>
        </div>
      </section>

      {summary && (
        <div className="bg-white p-5 rounded-xl border border-line shadow-sm">
          <h3 className="font-bold text-ink text-base flex items-center gap-2 mb-4">
            <BarChart3 className="h-5 w-5 text-teal-700" /> Incident Distribution Profiles
          </h3>
          <IncidentCharts summary={summary} />
        </div>
      )}
    </div>
  );
}
