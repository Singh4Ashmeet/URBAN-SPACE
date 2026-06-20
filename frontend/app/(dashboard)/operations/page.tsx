"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Activity, ShieldAlert, Award, Star, List, AlertTriangle, Truck, Compass, CheckCircle2 } from "lucide-react";
import { useRefresh } from "@/context/RefreshContext";
import { useAuth } from "@/context/AuthContext";
import { fetchIncidents, createDispatch, fetchVehicleRecommendations } from "@/lib/api";
import type { Incident } from "@/types/incidents";
import type { VehicleType } from "@/types/allocation";

export default function OperationsPage() {
  const { refreshTrigger, refresh } = useRefresh();
  const { canMutate } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Dispatch parameters
  const [vehicleCount, setVehicleCount] = useState(1);
  const [priority, setPriority] = useState(3);
  const [vehicleType, setVehicleType] = useState("");
  const [dispatchResult, setDispatchResult] = useState<any | null>(null);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null);

  const loadIncidents = useCallback(async () => {
    try {
      setLoading(true);
      const list = await fetchIncidents();
      // Only show active incidents for dispatch operations
      const active = list.filter((i) => !["RESOLVED", "CANCELLED"].includes(i.status));
      setIncidents(active);
      if (selectedIncident) {
        const updated = active.find((i) => i.id === selectedIncident.id);
        setSelectedIncident(updated || null);
      } else if (active.length > 0) {
        setSelectedIncident(active[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedIncident]);

  const loadRecommendations = useCallback(async () => {
    if (!selectedIncident) return;
    try {
      const recs = await fetchVehicleRecommendations(selectedIncident.id, vehicleType ? (vehicleType as VehicleType) : undefined);
      setRecommendations(recs);
    } catch (err) {
      console.error("Error loading recommendations:", err);
    }
  }, [selectedIncident, vehicleType]);

  useEffect(() => {
    loadIncidents();
  }, [refreshTrigger]);

  useEffect(() => {
    loadRecommendations();
  }, [selectedIncident, vehicleType, refreshTrigger]);

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncident) return;
    if (!canMutate) {
      setDispatchStatus("Current role cannot execute dispatches.");
      return;
    }
    setDispatching(true);
    setDispatchStatus(null);
    try {
      const res = await createDispatch({
        incidentId: selectedIncident.id,
        requestedVehicleCount: vehicleCount,
        priority,
        vehicleType: vehicleType ? (vehicleType as VehicleType) : undefined,
      });
      setDispatchResult(res);
      setDispatchStatus(res.assignments.length > 0 ? "Dispatch successful." : "No available units.");
      refresh();
    } catch (err) {
      console.error(err);
      setDispatchStatus("Dispatch execution failed.");
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-ink">Atomic Dispatch & Recommendation Room</h2>
        <p className="text-sm text-muted">deterministic vehicle suitability ranking with transparent scoring criteria.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        {/* Left Column: Active Incidents Selector */}
        <div className="bg-white rounded-xl border border-line p-4 shadow-sm space-y-4">
          <h3 className="font-bold text-ink text-base flex items-center gap-2">
            <List className="h-4.5 w-4.5 text-muted" /> Active Incident Queue
          </h3>
          <div className="space-y-2.5 overflow-auto max-h-[500px]">
            {incidents.map((inc) => (
              <article
                key={inc.id}
                onClick={() => {
                  setSelectedIncident(inc);
                  setDispatchResult(null);
                  setDispatchStatus(null);
                }}
                className={`rounded-lg border p-3.5 cursor-pointer transition ${
                  selectedIncident?.id === inc.id ? "border-teal-500 bg-teal-50" : "border-line bg-white hover:bg-slate-50"
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-ink">
                    Incident #{inc.id}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                    inc.severity >= 4 ? "bg-red-50 text-red-700" : "bg-slate-100 text-ink"
                  }`}>
                    Severity {inc.severity}
                  </span>
                </div>
                <h4 className="font-semibold text-ink text-sm mt-1.5 truncate">{inc.title}</h4>
                <p className="text-xs text-muted mt-1">
                  {inc.incidentType.replace("_", " ")} • {inc.status}
                </p>
              </article>
            ))}
            {incidents.length === 0 && (
              <p className="text-sm text-muted text-center py-6">All incidents resolved or queue empty.</p>
            )}
          </div>
        </div>

        {/* Right Column: Recommendations & Dispatch Console */}
        <div className="space-y-6">
          {selectedIncident ? (
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Recommendations */}
              <div className="bg-white rounded-xl border border-line p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-ink text-base flex items-center gap-2">
                    <Award className="h-5 w-5 text-teal-700" /> Deterministic Fleet Match
                  </h3>
                  <select
                    value={vehicleType}
                    onChange={(e) => setVehicleType(e.target.value)}
                    className="rounded border border-line px-2 py-1 text-xs focus:outline-none"
                  >
                    <option value="">Any Fleet Type</option>
                    {["AMBULANCE", "FIRE_ENGINE", "POLICE_CAR", "RESCUE_VEHICLE", "MOBILE_COMMAND_UNIT"].map((t) => (
                      <option key={t} value={t}>{t.replace("_", " ")}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-3 max-h-[450px] overflow-auto pr-1">
                  {recommendations.map((rec, idx) => (
                    <div
                      key={rec.vehicle.id}
                      className="rounded-lg border border-line p-3 text-sm space-y-2 bg-slate-50 hover:bg-slate-100/70 transition"
                    >
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          {idx === 0 && <Star className="h-4 w-4 text-amber-500 fill-amber-500" />}
                          <p className="font-bold text-ink">
                            {rec.vehicle.callSign} ({rec.vehicle.status})
                          </p>
                        </div>
                        <span className="font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded text-xs">
                          Score: {rec.score}
                        </span>
                      </div>
                      <p className="text-xs text-muted">
                        Type: {rec.vehicle.vehicleType.replace("_", " ")} • Home: {rec.vehicle.homeStation || "Mobile"}
                      </p>
                      
                      {/* Breakdown */}
                      <div className="pt-2 border-t border-line space-y-1">
                        <p className="text-[10px] font-bold text-muted uppercase">Telemetry Match Analysis</p>
                        <ul className="list-disc pl-3 text-[10px] text-muted space-y-0.5">
                          {rec.reasons.map((reason: string, rIdx: number) => (
                            <li key={rIdx}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ))}
                  {recommendations.length === 0 && (
                    <p className="text-sm text-muted text-center py-6">No matching fleet units found.</p>
                  )}
                </div>
              </div>

              {/* Atomic Dispatch Command */}
              <div className="space-y-6">
                <form onSubmit={handleDispatch} className="bg-white rounded-xl border border-line p-5 shadow-sm space-y-4">
                  <h3 className="font-bold text-ink text-base flex items-center gap-2">
                    <Compass className="h-5 w-5 text-indigo-700" /> Dispatch Execution Desk
                  </h3>

                  <div className="space-y-3.5">
                    <div>
                      <p className="text-xs font-semibold text-muted uppercase">Target Incident</p>
                      <p className="text-sm font-bold text-ink mt-0.5">{selectedIncident.title}</p>
                      <p className="text-xs text-muted">
                        Severity {selectedIncident.severity} • Coordinates {selectedIncident.latitude.toFixed(4)}, {selectedIncident.longitude.toFixed(4)}
                      </p>
                    </div>

                    <label className="grid gap-1 text-sm font-semibold text-ink">
                      Requested Vehicle Count
                      <input
                        type="number"
                        min="1"
                        max="10"
                        required
                        value={vehicleCount}
                        onChange={(e) => setVehicleCount(Number(e.target.value))}
                        className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
                      />
                    </label>

                    <label className="grid gap-1 text-sm font-semibold text-ink">
                      Priority Level (1-5)
                      <input
                        type="number"
                        min="1"
                        max="5"
                        required
                        value={priority}
                        onChange={(e) => setPriority(Number(e.target.value))}
                        className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
                      />
                    </label>
                  </div>

                  {dispatchStatus && (
                    <div className={`rounded-lg p-3 text-xs font-semibold flex items-center gap-2 border ${
                      dispatchResult?.assignments?.length > 0 ? "bg-teal-50 border-teal-200 text-teal-800" : "bg-red-50 border-red-200 text-red-800"
                    }`}>
                      {dispatchResult?.assignments?.length > 0 ? (
                        <CheckCircle2 className="h-4 w-4 text-teal-500 shrink-0" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                      )}
                      <span>{dispatchStatus}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={dispatching || recommendations.length === 0 || !canMutate}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 py-3 text-sm font-bold text-white transition disabled:opacity-50"
                  >
                    {dispatching ? "Executing Atomic Dispatch..." : "Execute Atomic Dispatch"}
                  </button>
                </form>

                {/* Dispatch assignments preview */}
                {dispatchResult && dispatchResult.assignments?.length > 0 && (
                  <div className="bg-white rounded-xl border border-line p-5 shadow-sm space-y-3">
                    <h4 className="font-bold text-ink text-sm">Dispatched Fleet Units</h4>
                    <div className="space-y-2.5">
                      {dispatchResult.assignments.map((assignment: any) => (
                        <div key={assignment.dispatchId} className="rounded-lg border border-line p-3 text-xs flex justify-between items-center bg-slate-50">
                          <div>
                            <p className="font-bold text-ink">
                              {assignment.vehicle.callSign}
                            </p>
                            <p className="text-muted mt-0.5">
                              Distance: {assignment.distanceKm} km • ETA: {assignment.estimatedArrivalMinutes} min
                            </p>
                          </div>
                          <span className="font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded">
                            Score: {assignment.score}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-xl border border-dashed border-line p-6 text-center text-muted text-sm">
              Select an active incident from the queue to start recommendation matches and execute atomic fleet dispatch operations.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
