"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { RefreshCw, Route, Navigation, ShieldAlert, AlertTriangle } from "lucide-react";
import { useRefresh } from "@/context/RefreshContext";
import { useAuth } from "@/context/AuthContext";
import { fetchDispatches, updateDispatchStatus } from "@/lib/api";
import type { DispatchRecord } from "@/types/allocation";

export default function DispatchesPage() {
  const { refreshTrigger, refresh } = useRefresh();
  const { canMutate } = useAuth();
  const [dispatches, setDispatches] = useState<DispatchRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDispatch, setSelectedDispatch] = useState<DispatchRecord | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchDispatches();
      setDispatches(res.content);
      if (selectedDispatch) {
        const updated = res.content.find((d) => d.id === selectedDispatch.id);
        setSelectedDispatch(updated || null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedDispatch]);

  useEffect(() => {
    loadData();
  }, [refreshTrigger, filterStatus]);

  const handleTransition = async (status: string) => {
    if (!selectedDispatch) return;
    if (!canMutate) {
      setErrorMsg("Current role cannot update dispatch state.");
      return;
    }
    setErrorMsg(null);
    try {
      const updated = await updateDispatchStatus(selectedDispatch.id, status);
      setSelectedDispatch(updated);
      refresh();
    } catch (err: any) {
      console.error(err);
      setErrorMsg("Transition rejected: The state transition is invalid for this dispatch.");
    }
  };

  const filteredDispatches = dispatches.filter(
    (d) => !filterStatus || d.status === filterStatus
  );

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-ink">Active Dispatches Control Room</h2>
        <p className="text-sm text-muted">Inspect active routes and progress dispatches through operational states.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_360px]">
        {/* Left Column: List of Dispatches */}
        <div className="bg-white rounded-xl border border-line shadow-sm p-4 space-y-4">
          <div className="flex items-center gap-4 border-b border-line pb-4 justify-between">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded-md border border-line px-3 py-2 text-sm focus:outline-none focus:border-teal-500 bg-white"
            >
              <option value="">All Statuses</option>
              {["ASSIGNED", "ACKNOWLEDGED", "ACCEPTED", "EN_ROUTE", "ARRIVED", "COMPLETED", "CANCELLED", "FAILED"].map((s) => (
                <option key={s} value={s}>{s.replace("_", " ")}</option>
              ))}
            </select>
            <span className="text-xs text-muted font-semibold">{filteredDispatches.length} matching</span>
          </div>

          <div className="space-y-3 overflow-auto max-h-[500px] pr-1">
            {filteredDispatches.map((d) => (
              <article
                key={d.id}
                onClick={() => {
                  setSelectedDispatch(d);
                  setErrorMsg(null);
                }}
                className={`rounded-xl border p-4 cursor-pointer hover:shadow-md transition flex items-start gap-3.5 ${
                  selectedDispatch?.id === d.id ? "border-teal-500 bg-teal-50" : "border-line bg-white"
                }`}
              >
                <span className="p-2.5 rounded-lg bg-indigo-50 text-indigo-700">
                  <Navigation className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex justify-between items-center">
                    <h4 className="font-bold text-ink text-base">Dispatch #{d.id}</h4>
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-slate-100 text-ink">
                      P{d.priority}
                    </span>
                  </div>
                  <p className="text-xs text-muted font-medium">Incident #{d.incident_id} • Vehicle #{d.vehicle_id}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      d.status === "COMPLETED" ? "bg-teal-100 text-teal-800" :
                      d.status === "CANCELLED" || d.status === "FAILED" ? "bg-red-100 text-red-800" : "bg-blue-100 text-blue-800"
                    }`}>
                      {d.status}
                    </span>
                    <span className="text-xs text-muted">• {d.distance_km} km</span>
                  </div>
                </div>
              </article>
            ))}
            {filteredDispatches.length === 0 && (
              <p className="text-sm text-muted text-center py-6">No dispatches found.</p>
            )}
          </div>
        </div>

        {/* Right Column: Selected Dispatch Actions */}
        <div className="space-y-6">
          {selectedDispatch ? (
            <div className="bg-white rounded-xl border border-line shadow-sm p-5 space-y-4">
              <div className="border-b border-line pb-3">
                <h3 className="font-bold text-ink text-lg">Dispatch #{selectedDispatch.id}</h3>
                <p className="text-xs text-muted">Created: {new Date(selectedDispatch.created_at).toLocaleString()}</p>
              </div>

              {errorMsg && (
                <div className="rounded-lg bg-red-50 border border-red-200 p-3 flex items-start gap-2 text-xs font-semibold text-red-700">
                  <AlertTriangle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted">Route Status:</span>
                  <span className="font-bold text-ink">{selectedDispatch.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Target Incident:</span>
                  <Link href={`/incidents/${selectedDispatch.incident_id}`} className="font-bold text-teal-600 hover:underline">
                    Incident #{selectedDispatch.incident_id}
                  </Link>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Assigned Unit:</span>
                  <span className="font-bold text-ink">Vehicle #{selectedDispatch.vehicle_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Distance:</span>
                  <span className="font-bold text-ink">{selectedDispatch.distance_km} km</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Estimated Arrival:</span>
                  <span className="font-bold text-ink">{selectedDispatch.estimated_arrival_minutes} mins</span>
                </div>
                <div className="pt-2 border-t border-line">
                  <span className="text-xs font-semibold text-muted uppercase">Reasoning Details</span>
                  <p className="text-xs leading-relaxed text-muted mt-1 bg-slate-50 p-2.5 rounded border border-line font-medium">
                    {selectedDispatch.assignment_reason}
                  </p>
                </div>
              </div>

              {/* Status Update Transition Actions */}
              <div className="border-t border-line pt-4 space-y-2">
                <p className="text-xs font-semibold text-muted uppercase">State Transitions</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleTransition("ACKNOWLEDGED")}
                    disabled={selectedDispatch.status === "ACKNOWLEDGED"}
                    className="rounded border border-line px-2 py-1.5 text-xs font-bold hover:bg-slate-50 disabled:opacity-50"
                  >
                    Acknowledge
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTransition("EN_ROUTE")}
                    disabled={selectedDispatch.status === "EN_ROUTE"}
                    className="rounded border border-line px-2 py-1.5 text-xs font-bold hover:bg-slate-50 disabled:opacity-50"
                  >
                    En Route
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTransition("ARRIVED")}
                    disabled={selectedDispatch.status === "ARRIVED"}
                    className="rounded border border-line px-2 py-1.5 text-xs font-bold hover:bg-slate-50 disabled:opacity-50"
                  >
                    Mark Arrived
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTransition("COMPLETED")}
                    disabled={selectedDispatch.status === "COMPLETED"}
                    className="rounded border border-line px-2.5 py-1.5 text-xs font-bold text-teal-800 bg-teal-50 hover:bg-teal-100 disabled:opacity-50"
                  >
                    Complete
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTransition("CANCELLED")}
                    disabled={selectedDispatch.status === "CANCELLED"}
                    className="rounded border border-line px-2.5 py-1.5 text-xs font-bold text-amber-850 bg-amber-50 hover:bg-amber-100 col-span-2 disabled:opacity-50"
                  >
                    Cancel Dispatch
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-xl border border-dashed border-line p-6 text-center text-muted text-sm">
              Select an active dispatch from the list to view its route history, assignment reasons, or execute state transitions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
