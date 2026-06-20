"use client";

import type { IncidentFilters } from "@/types/incidents";

type IncidentFiltersProps = {
  filters: IncidentFilters;
  onChange: (filters: IncidentFilters) => void;
};

const incidentTypes = ["", "ACCIDENT", "FIRE", "FLOOD", "ROAD_CLOSURE", "TRAFFIC_JAM", "MEDICAL_EMERGENCY", "PUBLIC_HAZARD"];
const statuses = ["", "REPORTED", "VERIFIED", "IN_PROGRESS", "RESOLVED", "CANCELLED"];

export function IncidentFilters({ filters, onChange }: IncidentFiltersProps) {
  return (
    <section className="rounded-lg border border-line bg-white p-4" aria-labelledby="filters-heading">
      <h2 id="filters-heading" className="text-lg font-semibold text-ink">Filters</h2>
      <div className="mt-4 grid gap-3">
        <label className="grid gap-1 text-sm font-medium text-ink">
          Incident type
          <select className="rounded-md border border-line px-3 py-2" value={filters.incidentType} onChange={(event) => onChange({ ...filters, incidentType: event.target.value })}>
            {incidentTypes.map((type) => <option key={type} value={type}>{type ? type.replaceAll("_", " ") : "All types"}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium text-ink">
          Status
          <select className="rounded-md border border-line px-3 py-2" value={filters.status} onChange={(event) => onChange({ ...filters, status: event.target.value })}>
            {statuses.map((status) => <option key={status} value={status}>{status ? status.replaceAll("_", " ") : "All statuses"}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium text-ink">
          Minimum severity
          <input className="rounded-md border border-line px-3 py-2" type="number" min="1" max="5" value={filters.minimumSeverity} onChange={(event) => onChange({ ...filters, minimumSeverity: event.target.value })} />
        </label>
      </div>
    </section>
  );
}
