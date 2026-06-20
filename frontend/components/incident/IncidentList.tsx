"use client";

import type { Incident } from "@/types/incidents";

type IncidentListProps = {
  incidents: Incident[];
  selectedIncident: Incident | null;
  onSelectIncident: (incident: Incident) => void;
  onResolveIncident?: (incident: Incident) => void;
  onDeleteIncident?: (incident: Incident) => void;
};

export function IncidentList({ incidents, selectedIncident, onSelectIncident, onResolveIncident, onDeleteIncident }: IncidentListProps) {
  return (
    <section className="rounded-lg border border-line bg-white p-4" aria-labelledby="incident-list-heading">
      <h2 id="incident-list-heading" className="text-lg font-semibold text-ink">Incident list</h2>
      <div className="mt-4 max-h-[420px] space-y-3 overflow-auto pr-1">
        {incidents.length === 0 ? (
          <p className="text-sm text-muted">No incidents match the current filters.</p>
        ) : (
          incidents.map((incident) => (
            <article
              key={incident.id}
              className={`rounded-lg border p-3 ${selectedIncident?.id === incident.id ? "border-teal-500 bg-teal-50" : "border-line bg-white"}`}
            >
              <button type="button" onClick={() => onSelectIncident(incident)} className="block w-full text-left">
                <span className="text-sm font-semibold text-ink">{incident.title}</span>
                <span className="mt-1 block text-xs text-muted">
                  {incident.incidentType.replaceAll("_", " ")} · Severity {incident.severity} · {incident.status.replaceAll("_", " ")}
                </span>
              </button>
              {(onResolveIncident || onDeleteIncident) && (
                <div className="mt-3 flex gap-2">
                  {onResolveIncident && (
                    <button type="button" onClick={() => onResolveIncident(incident)} className="rounded-md border border-teal-700 px-3 py-2 text-xs font-semibold text-teal-700">
                      Resolve
                    </button>
                  )}
                  {onDeleteIncident && (
                    <button type="button" onClick={() => onDeleteIncident(incident)} className="rounded-md border border-danger-500 px-3 py-2 text-xs font-semibold text-danger-500">
                      Delete
                    </button>
                  )}
                </div>
              )}
            </article>
          ))
        )}
      </div>
    </section>
  );
}
