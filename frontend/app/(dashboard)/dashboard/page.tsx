"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { AlertTriangle, Ambulance, Activity, ClipboardList, PlayCircle, Route, CheckCircle2, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRefresh } from "@/context/RefreshContext";
import { fetchIncidents, fetchIncidentSummary, fetchVehicles, fetchDispatches, fetchNearbyVehicles } from "@/lib/api";
import { CityMap } from "@/components/map/CityMap";
import type { Incident, IncidentSummary } from "@/types/incidents";
import type { EmergencyVehicle, DispatchRecord } from "@/types/allocation";

export default function DashboardPage() {
  const { refreshTrigger } = useRefresh();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [vehicles, setVehicles] = useState<EmergencyVehicle[]>([]);
  const [dispatches, setDispatches] = useState<DispatchRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [nextIncidents, nextSummary, nextVehicles, nextDispatches] = await Promise.all([
        fetchIncidents(),
        fetchIncidentSummary(),
        fetchVehicles(),
        fetchDispatches(),
      ]);
      setIncidents(nextIncidents);
      setSummary(nextSummary);
      setVehicles(nextVehicles.content);
      setDispatches(nextDispatches.content);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData, refreshTrigger]);

  const activeIncidents = useMemo(() => incidents.filter((incident) => !["RESOLVED", "CANCELLED"].includes(incident.status)).length, [incidents]);
  const criticalIncidents = useMemo(() => incidents.filter((incident) => incident.severity >= 4).length, [incidents]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* Metrics */}
      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard icon={ClipboardList} label="Total Incidents" value={String(incidents.length)} />
        <MetricCard icon={Activity} label="Active Incidents" value={String(activeIncidents)} />
        <MetricCard icon={AlertTriangle} label="Critical Severity" value={String(criticalIncidents)} tone="warn" />
        <MetricCard icon={CheckCircle2} label="Services Status" value="Online" tone="good" />
      </section>

      {/* Main Grid */}
      <section className="grid gap-6 2xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
        {/* Map Panel */}
        <div className="space-y-3 bg-white p-4 rounded-xl border border-line shadow-sm">
          <div>
            <h3 className="text-lg font-bold text-ink">Live Operations Map</h3>
            <p className="text-sm text-muted">Real-time status of incidents and emergency vehicles.</p>
          </div>
          <div className="h-[500px] overflow-hidden rounded-lg border border-line">
            <CityMap
              incidents={incidents}
              selectedIncident={null}
              onSelectIncident={() => {}}
              is3d={false}
              scenarioPoint={null}
              onPlaceScenario={() => {}}
              vehicles={vehicles}
            />
          </div>
        </div>

        {/* Right Side Panels */}
        <div className="space-y-6">
          {/* Simulation Studio Card */}
          <div className="bg-white p-5 rounded-xl border border-line shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <span className="rounded-lg bg-teal-50 p-2 text-teal-700">
                <PlayCircle className="h-5 w-5" />
              </span>
              <div>
                <h3 className="font-bold text-ink text-base">Simulation Studio</h3>
                <p className="text-xs text-muted">Test response scenarios & route ETAs</p>
              </div>
            </div>
            <p className="text-sm leading-relaxed text-muted">
              Configure parameters such as road blocks, vehicle counts, weather and traffic levels to predict risk and estimate response times.
            </p>
            <Link href="/simulations" className="block text-center rounded-lg bg-teal-600 hover:bg-teal-700 py-3 text-sm font-semibold text-white transition">
              Launch Simulation Setup
            </Link>
          </div>

          {/* Incident Queue Card */}
          <div className="bg-white p-5 rounded-xl border border-line shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="rounded-lg bg-amber-50 p-2 text-amber-700">
                  <AlertTriangle className="h-5 w-5" />
                </span>
                <h3 className="font-bold text-ink text-base">Active Incidents</h3>
              </div>
              <Link href="/incidents" className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center">
                View All <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            <div className="divide-y divide-line">
              {incidents.slice(0, 4).map((incident) => (
                <div key={incident.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-ink truncate">{incident.title}</p>
                    <p className="text-xs text-muted truncate">
                      {incident.incidentType.replace("_", " ")} • {incident.status}
                    </p>
                  </div>
                  <span className={`rounded px-2 py-0.5 text-xs font-bold ${
                    incident.severity >= 4 ? "bg-red-50 text-red-700" : "bg-slate-100 text-ink"
                  }`}>
                    S{incident.severity}
                  </span>
                </div>
              ))}
              {incidents.length === 0 && (
                <p className="text-sm text-muted text-center py-4">No incidents reported.</p>
              )}
            </div>
          </div>

          {/* Allocation Panel Preview */}
          <div className="bg-white p-5 rounded-xl border border-line shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="rounded-lg bg-indigo-50 p-2 text-indigo-700">
                  <Route className="h-5 w-5" />
                </span>
                <h3 className="font-bold text-ink text-base">Dispatches Status</h3>
              </div>
              <Link href="/dispatches" className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center">
                Manage <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            <div className="space-y-3">
              {dispatches.slice(0, 3).map((d) => (
                <div key={d.id} className="rounded-lg border border-line p-3 text-sm flex justify-between items-center bg-slate-50">
                  <div>
                    <p className="font-semibold text-ink">Dispatch #{d.id}</p>
                    <p className="text-xs text-muted">Incident #{d.incident_id} • {d.distance_km} km</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                    d.status === "COMPLETED" ? "bg-teal-50 text-teal-700" : "bg-blue-50 text-blue-700"
                  }`}>
                    {d.status}
                  </span>
                </div>
              ))}
              {dispatches.length === 0 && (
                <p className="text-sm text-muted text-center py-4">No dispatches recorded.</p>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, tone = "default" }: { icon: any; label: string; value: string; tone?: "default" | "good" | "warn" }) {
  const colors = tone === "good" ? "bg-teal-50 text-teal-750" : tone === "warn" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-ink";
  return (
    <article className="rounded-xl border border-line bg-white p-5 shadow-sm hover:shadow-md transition">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-muted">{label}</p>
        <span className={`rounded-lg p-2.5 ${colors}`}><Icon className="h-4.5 w-4.5" /></span>
      </div>
      <p className="mt-3 text-3xl font-bold text-ink">{value}</p>
    </article>
  );
}
