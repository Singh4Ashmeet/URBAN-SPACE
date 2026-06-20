"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ChevronRight, PlusCircle, RefreshCw } from "lucide-react";
import { useRefresh } from "@/context/RefreshContext";
import { useAuth } from "@/context/AuthContext";
import { fetchIncidents, createIncident, updateIncidentStatus, deleteIncident } from "@/lib/api";
import { IncidentFilters } from "@/components/incident/IncidentFilters";
import { IncidentList } from "@/components/incident/IncidentList";
import { CityMap } from "@/components/map/CityMap";
import type { Incident, IncidentFilters as IncidentFiltersType, IncidentType } from "@/types/incidents";

const initialFilters: IncidentFiltersType = { incidentType: "", status: "", minimumSeverity: "" };

export default function IncidentsPage() {
  const { refreshTrigger, refresh } = useRefresh();
  const { canMutate } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [filters, setFilters] = useState<IncidentFiltersType>(initialFilters);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);

  // New incident form state (inline or dialog)
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState<IncidentType>("ACCIDENT");
  const [newSeverity, setNewSeverity] = useState(3);
  const [newDesc, setNewDesc] = useState("");
  const [newLat, setNewLat] = useState(28.6139);
  const [newLng, setNewLng] = useState(77.2090);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const nextIncidents = await fetchIncidents(filters);
      setIncidents(nextIncidents);
      // Keep selected incident reference updated
      if (selectedIncident) {
        const updated = nextIncidents.find((i) => i.id === selectedIncident.id);
        setSelectedIncident(updated || null);
      }
    } catch (err) {
      console.error("Error fetching incidents:", err);
    } finally {
      setLoading(false);
    }
  }, [filters, selectedIncident]);

  useEffect(() => {
    loadData();
  }, [refreshTrigger, filters]);

  const handleResolve = async (incident: Incident) => {
    try {
      await updateIncidentStatus(incident.id, "RESOLVED");
      refresh();
    } catch (err) {
      console.error("Error resolving incident:", err);
    }
  };

  const handleDelete = async (incident: Incident) => {
    if (window.confirm(`Delete ${incident.title}?`)) {
      try {
        await deleteIncident(incident.id);
        setSelectedIncident(null);
        refresh();
      } catch (err) {
        console.error("Error deleting incident:", err);
      }
    }
  };

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await createIncident({
        title: newTitle,
        description: newDesc,
        incidentType: newType,
        severity: newSeverity,
        status: "REPORTED",
        latitude: newLat,
        longitude: newLng,
      });
      setShowCreateForm(false);
      setNewTitle("");
      setNewDesc("");
      setSelectedIncident(created);
      refresh();
    } catch (err) {
      console.error("Error creating incident:", err);
    }
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">Incidents Operations Room</h2>
          <p className="text-sm text-muted">Create, inspect, and route dispatches for smart city incidents.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateForm(!showCreateForm)}
          disabled={!canMutate}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 hover:bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white transition disabled:opacity-50"
        >
          <PlusCircle className="h-4 w-4" /> {showCreateForm ? "Cancel Creation" : "Create Incident"}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreateIncident} className="bg-white p-5 rounded-xl border border-line shadow-sm max-w-xl space-y-4">
          <h3 className="font-bold text-ink text-base">New Smart City Incident</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Title
              <input
                type="text"
                required
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
                placeholder="Bridge lane collision..."
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Incident Type
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as IncidentType)}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              >
                {["ACCIDENT", "FIRE", "FLOOD", "ROAD_CLOSURE", "TRAFFIC_JAM", "MEDICAL_EMERGENCY", "PUBLIC_HAZARD"].map((t) => (
                  <option key={t} value={t}>{t.replace("_", " ")}</option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Severity (1-5)
              <input
                type="number"
                min="1"
                max="5"
                value={newSeverity}
                onChange={(e) => setNewSeverity(Number(e.target.value))}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Description
              <input
                type="text"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
                placeholder="Details of the collision..."
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Latitude
              <input
                type="number"
                step="0.0001"
                value={newLat}
                onChange={(e) => setNewLat(Number(e.target.value))}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Longitude
              <input
                type="number"
                step="0.0001"
                value={newLng}
                onChange={(e) => setNewLng(Number(e.target.value))}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
          </div>
          <button
            type="submit"
            className="w-full rounded-lg bg-teal-600 hover:bg-teal-700 py-2.5 text-sm font-bold text-white transition"
          >
            Submit Incident Report
          </button>
        </form>
      )}

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-6">
          <IncidentFilters filters={filters} onChange={setFilters} />
          <IncidentList
            incidents={incidents}
            selectedIncident={selectedIncident}
            onSelectIncident={setSelectedIncident}
            onResolveIncident={canMutate ? handleResolve : undefined}
            onDeleteIncident={canMutate ? handleDelete : undefined}
          />
        </div>

        <div className="space-y-6">
          {selectedIncident && (
            <div className="bg-teal-50 border border-teal-200 p-4 rounded-xl shadow-sm flex flex-wrap items-center justify-between gap-4">
              <div>
                <h4 className="font-bold text-teal-900 text-lg">{selectedIncident.title}</h4>
                <p className="text-sm text-teal-700">
                  {selectedIncident.incidentType.replace("_", " ")} • Severity {selectedIncident.severity} • {selectedIncident.status}
                </p>
              </div>
              <Link
                href={`/incidents/${selectedIncident.id}`}
                className="inline-flex items-center gap-2 rounded-lg bg-teal-600 hover:bg-teal-700 px-4 py-2.5 text-sm font-bold text-white transition"
              >
                Inspect History & Details <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          )}

          <div className="bg-white p-4 rounded-xl border border-line shadow-sm h-[500px] overflow-hidden">
            <CityMap
              incidents={incidents}
              selectedIncident={selectedIncident}
              onSelectIncident={setSelectedIncident}
              is3d={false}
              scenarioPoint={null}
              onPlaceScenario={() => {}}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
