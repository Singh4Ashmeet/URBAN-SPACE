"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, Clock, History, Route, Trash2, CheckCircle2, Shield } from "lucide-react";
import { fetchIncidentById, fetchIncidentHistory, updateIncidentStatus, deleteIncident, fetchDispatches } from "@/lib/api";
import { useRefresh } from "@/context/RefreshContext";
import type { Incident } from "@/types/incidents";
import type { DispatchRecord } from "@/types/allocation";

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { refreshTrigger, refresh } = useRefresh();
  const id = Number(params.id);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [dispatches, setDispatches] = useState<DispatchRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id || isNaN(id)) return;
    try {
      setLoading(true);
      const [incData, historyData, dispatchesData] = await Promise.all([
        fetchIncidentById(id),
        fetchIncidentHistory(id),
        fetchDispatches()
      ]);
      setIncident(incData);
      setHistory(historyData);
      // Filter dispatches for this incident
      setDispatches(dispatchesData.content.filter((d) => d.incident_id === id));
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError("Incident not found or network error.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData, refreshTrigger]);

  const handleStatusUpdate = async (status: string) => {
    if (!incident) return;
    try {
      await updateIncidentStatus(incident.id, status);
      refresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async () => {
    if (!incident) return;
    if (window.confirm(`Are you sure you want to delete incident #${incident.id}?`)) {
      try {
        await deleteIncident(incident.id);
        router.push("/incidents");
      } catch (err) {
        console.error(err);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent"></div>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="p-6 space-y-4 max-w-lg mx-auto text-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto" />
        <h3 className="text-xl font-bold text-ink">Incident Details Error</h3>
        <p className="text-muted text-sm">{error || "Could not retrieve the incident info."}</p>
        <Link href="/incidents" className="inline-block bg-teal-600 text-white rounded-lg px-4 py-2 text-sm font-semibold">
          Back to List
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-6xl mx-auto">
      <Link href="/incidents" className="inline-flex items-center gap-2 text-sm font-semibold text-teal-600 hover:text-teal-700">
        <ArrowLeft className="h-4 w-4" /> Back to Incidents Rooms
      </Link>

      <div className="grid gap-6 md:grid-cols-[1fr_320px]">
        {/* Left column: Info & Timeline */}
        <div className="space-y-6">
          {/* Main Info */}
          <div className="bg-white p-6 rounded-xl border border-line shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                incident.severity >= 4 ? "bg-red-50 text-red-700" : "bg-slate-100 text-ink"
              }`}>
                Severity Level {incident.severity}
              </span>
              <span className="text-xs text-muted">Version #{incident.version}</span>
            </div>
            <h3 className="text-2xl font-bold text-ink">{incident.title}</h3>
            <p className="text-sm leading-relaxed text-muted">
              {incident.description || "No description provided."}
            </p>
            <div className="grid gap-4 sm:grid-cols-2 text-sm pt-2">
              <div>
                <p className="text-xs font-semibold text-muted uppercase">Type</p>
                <p className="font-semibold text-ink mt-0.5">{incident.incidentType.replace("_", " ")}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-muted uppercase">Status</p>
                <p className="font-semibold text-ink mt-0.5">{incident.status}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-muted uppercase">Location</p>
                <p className="font-semibold text-ink mt-0.5">{incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-muted uppercase">District</p>
                <p className="font-semibold text-ink mt-0.5">{incident.district || "Default District"}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-muted uppercase">Reported At</p>
                <p className="font-semibold text-ink mt-0.5">
                  {incident.reportedAt ? new Date(incident.reportedAt).toLocaleString() : "Unknown"}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-muted uppercase">Resolved At</p>
                <p className="font-semibold text-ink mt-0.5">
                  {incident.resolvedAt ? new Date(incident.resolvedAt).toLocaleString() : "Still Active"}
                </p>
              </div>
            </div>
          </div>

          {/* History / Audit Timeline */}
          <div className="bg-white p-6 rounded-xl border border-line shadow-sm space-y-4">
            <div className="flex items-center gap-2.5 pb-2 border-b border-line">
              <History className="h-5 w-5 text-teal-700" />
              <h3 className="font-bold text-ink text-lg">History & Audit Logs</h3>
            </div>
            <div className="relative border-l-2 border-slate-100 pl-4 ml-2 space-y-6">
              {history.map((log) => (
                <div key={log.id} className="relative space-y-1">
                  <span className="absolute -left-[25px] top-1.5 h-3 w-3 rounded-full bg-teal-500 ring-4 ring-white" />
                  <div className="flex items-center justify-between text-xs text-muted">
                    <span className="font-bold text-teal-700">{log.action}</span>
                    <span>{new Date(log.createdAt).toLocaleString()}</span>
                  </div>
                  {log.snapshot && (
                    <div className="bg-slate-50 p-2.5 rounded text-xs font-mono text-muted overflow-auto max-h-48 mt-1">
                      <pre>{JSON.stringify(log.snapshot, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ))}
              {history.length === 0 && (
                <p className="text-sm text-muted py-2">No history logs recorded.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right column: Action controls */}
        <div className="space-y-6">
          {/* Status Actions */}
          <div className="bg-white p-5 rounded-xl border border-line shadow-sm space-y-4">
            <h4 className="font-bold text-ink text-base">Resolution Desk</h4>
            <div className="grid gap-2">
              <button
                type="button"
                onClick={() => handleStatusUpdate("VERIFIED")}
                disabled={incident.status === "VERIFIED"}
                className="w-full text-left px-3 py-2 rounded-lg text-sm font-semibold border border-line hover:bg-slate-50 disabled:opacity-50 disabled:bg-slate-50"
              >
                Mark Verified
              </button>
              <button
                type="button"
                onClick={() => handleStatusUpdate("IN_PROGRESS")}
                disabled={incident.status === "IN_PROGRESS"}
                className="w-full text-left px-3 py-2 rounded-lg text-sm font-semibold border border-line hover:bg-slate-50 disabled:opacity-50 disabled:bg-slate-50"
              >
                Mark In Progress
              </button>
              <button
                type="button"
                onClick={() => handleStatusUpdate("RESOLVED")}
                disabled={incident.status === "RESOLVED"}
                className="w-full text-left px-3 py-2 rounded-lg text-sm font-semibold text-teal-800 bg-teal-50 hover:bg-teal-100 disabled:opacity-50"
              >
                Mark Resolved
              </button>
              <button
                type="button"
                onClick={() => handleStatusUpdate("CANCELLED")}
                disabled={incident.status === "CANCELLED"}
                className="w-full text-left px-3 py-2 rounded-lg text-sm font-semibold text-amber-800 bg-amber-50 hover:bg-amber-100 disabled:opacity-50"
              >
                Mark Cancelled
              </button>
            </div>
            <button
              type="button"
              onClick={handleDelete}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-red-50 hover:bg-red-100 py-2.5 text-sm font-bold text-red-600 transition border border-red-200"
            >
              <Trash2 className="h-4 w-4" /> Delete Incident
            </button>
          </div>

          {/* Active Dispatches */}
          <div className="bg-white p-5 rounded-xl border border-line shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <Route className="h-5 w-5 text-indigo-700" />
              <h4 className="font-bold text-ink text-base">Active Dispatches</h4>
            </div>
            <div className="space-y-3">
              {dispatches.map((d) => (
                <div key={d.id} className="rounded-lg border border-line p-3 text-sm space-y-1 bg-slate-50">
                  <div className="flex justify-between items-center">
                    <p className="font-bold text-ink">Dispatch #{d.id}</p>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                      {d.status}
                    </span>
                  </div>
                  <p className="text-xs text-muted">Vehicle #{d.vehicle_id} • {d.distance_km} km</p>
                  <p className="text-xs text-muted">ETA: {d.estimated_arrival_minutes} mins</p>
                </div>
              ))}
              {dispatches.length === 0 && (
                <p className="text-xs text-muted text-center py-4">No dispatches for this incident.</p>
              )}
            </div>
            {incident.status !== "RESOLVED" && incident.status !== "CANCELLED" && (
              <Link
                href="/operations"
                className="block text-center rounded-lg bg-indigo-600 hover:bg-indigo-700 py-2.5 text-sm font-bold text-white transition"
              >
                Dispatch Vehicle
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
