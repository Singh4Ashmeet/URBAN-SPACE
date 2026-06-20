"use client";

import { Download, RotateCcw, Save, Send } from "lucide-react";
import type { SimulationRequest, SimulationResponse, TrafficLevel, WeatherCondition } from "@/types/simulation";
import type { IncidentType } from "@/types/incidents";

type ScenarioBuilderProps = {
  value: SimulationRequest;
  onChange: (value: SimulationRequest) => void;
  onRun: () => void;
  onSaveDraft: () => void;
  isRunning: boolean;
  progressEvents: string[];
  result: SimulationResponse | null;
};

const incidentTypes: IncidentType[] = ["ACCIDENT", "FIRE", "FLOOD", "ROAD_CLOSURE", "TRAFFIC_JAM", "MEDICAL_EMERGENCY", "PUBLIC_HAZARD"];
const trafficLevels: TrafficLevel[] = ["LOW", "MODERATE", "HIGH", "SEVERE"];
const weatherConditions: WeatherCondition[] = ["CLEAR", "RAIN", "HEAVY_RAIN", "FOG", "STORM"];

export function ScenarioBuilder({ value, onChange, onRun, onSaveDraft, isRunning, progressEvents, result }: ScenarioBuilderProps) {
  const update = <K extends keyof SimulationRequest>(key: K, nextValue: SimulationRequest[K]) => onChange({ ...value, [key]: nextValue });

  return (
    <section className="rounded-lg border border-line bg-white p-4" aria-labelledby="scenario-heading">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="scenario-heading" className="text-lg font-semibold text-ink">Scenario Controls</h2>
          <p className="mt-1 text-sm text-muted">Configure inputs, confirm the map point, then run the response model.</p>
        </div>
        <button type="button" className="rounded-md border border-line p-2 text-muted" onClick={() => onChange(defaultScenario())} aria-label="Reset scenario">
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 grid gap-3">
        <label className="grid gap-1 text-sm font-medium text-ink">
          Scenario name
          <input className="rounded-md border border-line px-3 py-2" value={value.scenario_name} onChange={(event) => update("scenario_name", event.target.value)} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1 text-sm font-medium text-ink">
            Incident type
            <select className="rounded-md border border-line px-3 py-2" value={value.incident_type} onChange={(event) => update("incident_type", event.target.value as IncidentType)}>
              {incidentTypes.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-medium text-ink">
            Severity
            <input className="rounded-md border border-line px-3 py-2" type="number" min="1" max="5" value={value.severity} onChange={(event) => update("severity", Number(event.target.value))} />
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1 text-sm font-medium text-ink">
            Traffic
            <select className="rounded-md border border-line px-3 py-2" value={value.traffic_level} onChange={(event) => update("traffic_level", event.target.value as TrafficLevel)}>
              {trafficLevels.map((level) => <option key={level} value={level}>{level.replaceAll("_", " ")}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-medium text-ink">
            Weather
            <select className="rounded-md border border-line px-3 py-2" value={value.weather_condition} onChange={(event) => update("weather_condition", event.target.value as WeatherCondition)}>
              {weatherConditions.map((condition) => <option key={condition} value={condition}>{condition.replaceAll("_", " ")}</option>)}
            </select>
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1 text-sm font-medium text-ink">
            Vehicles
            <input className="rounded-md border border-line px-3 py-2" type="number" min="1" max="20" value={value.number_of_vehicles} onChange={(event) => update("number_of_vehicles", Number(event.target.value))} />
          </label>
          <label className="grid gap-1 text-sm font-medium text-ink">
            Duration
            <input className="rounded-md border border-line px-3 py-2" type="number" min="5" max="240" value={value.simulation_duration_minutes} onChange={(event) => update("simulation_duration_minutes", Number(event.target.value))} />
          </label>
        </div>
        <label className="flex items-center gap-2 text-sm font-medium text-ink">
          <input type="checkbox" checked={value.road_blocked} onChange={(event) => update("road_blocked", event.target.checked)} />
          Road blocked
        </label>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_auto]">
        <button type="button" onClick={onRun} disabled={isRunning || !value.scenario_name.trim()} className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-700 px-5 py-3 text-sm font-semibold text-white shadow-soft disabled:opacity-60">
          <Send className="h-4 w-4" /> {isRunning ? "Running simulation..." : "Run simulation"}
        </button>
        <button type="button" onClick={onSaveDraft} className="inline-flex items-center justify-center gap-2 rounded-md border border-line px-4 py-3 text-sm font-semibold text-ink">
          <Save className="h-4 w-4" /> Save draft
        </button>
      </div>

      <div className="mt-4" aria-live="polite">
        <h3 className="text-sm font-semibold text-ink">Progress</h3>
        <ol className="mt-2 flex flex-wrap gap-2 text-xs">
          {progressEvents.length === 0 ? <li className="text-muted">Waiting to run.</li> : progressEvents.map((event, index) => (
            <li key={`${event}-${index}`} className="rounded-md bg-teal-50 px-2 py-1 font-semibold text-teal-700">{event.replaceAll("_", " ")}</li>
          ))}
        </ol>
      </div>

      {result ? (
        <div className="mt-4 rounded-lg border border-line bg-slate-50 p-4">
          <h3 className="text-base font-semibold text-ink">Scenario results</h3>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <Metric label="Risk score" value={`${result.risk_score}/100`} />
            <Metric label="Response time" value={`${result.estimated_response_time_minutes} min`} />
            <Metric label="Affected radius" value={`${result.estimated_affected_radius_meters} m`} />
            <Metric label="Route distance" value={`${result.route_distance_km} km`} />
            <Metric label="Recommended vehicles" value={String(result.recommended_vehicle_count)} />
            <Metric label="Status" value={result.status.replaceAll("_", " ")} />
          </dl>
          {result.warnings.length > 0 ? <p className="mt-3 text-sm text-amber-500">{result.warnings.join(" ")}</p> : null}
          <button
            type="button"
            className="mt-3 inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-semibold text-ink"
            onClick={() => downloadJson(result)}
          >
            <Download className="h-4 w-4" /> Export JSON
          </button>
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="font-semibold text-ink">{value}</dd>
    </div>
  );
}

export function defaultScenario(): SimulationRequest {
  return {
    scenario_name: "Demo response scenario",
    incident_type: "ACCIDENT",
    severity: 3,
    latitude: 28.6139,
    longitude: 77.209,
    number_of_vehicles: 2,
    traffic_level: "MODERATE",
    weather_condition: "CLEAR",
    road_blocked: false,
    simulation_duration_minutes: 30
  };
}

function downloadJson(result: SimulationResponse) {
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${result.simulation_id}.json`;
  link.click();
  URL.revokeObjectURL(url);
}
