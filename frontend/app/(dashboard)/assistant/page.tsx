"use client";

import { useEffect, useState } from "react";
import { Bot, BrainCircuit, ClipboardList, Lightbulb, RefreshCw, ShieldAlert } from "lucide-react";
import { fetchAiHealth, fetchAiModels, fetchIncidents, requestAi } from "@/lib/api";
import type { Incident } from "@/types/incidents";

type Operation = "incident-priority" | "dispatch-brief" | "scenario-explanation";

export default function AssistantPage() {
  const [health, setHealth] = useState<any | null>(null);
  const [models, setModels] = useState<any | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(null);
  const [operation, setOperation] = useState<Operation>("incident-priority");
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const selectedIncident = incidents.find((item) => item.id === selectedIncidentId) ?? incidents[0];

  async function load() {
    setLoading(true);
    const [healthRes, modelsRes, incidentRes] = await Promise.all([fetchAiHealth(), fetchAiModels(), fetchIncidents()]);
    setHealth(healthRes);
    setModels(modelsRes);
    setIncidents(incidentRes);
    setSelectedIncidentId((current) => current ?? incidentRes[0]?.id ?? null);
    setLoading(false);
  }

  useEffect(() => {
    load().catch(() => setLoading(false));
  }, []);

  async function runAssistant() {
    setRunning(true);
    try {
      const payload =
        operation === "scenario-explanation"
          ? { simulation: { scenario_name: selectedIncident?.title ?? "Current operations", severity: selectedIncident?.severity ?? 2, risk_score: (selectedIncident?.severity ?? 2) * 18 }, incident: selectedIncident }
          : { incident: selectedIncident, dispatches: [] };
      setResult(await requestAi(operation, payload));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-ink">Local AI Assistant</h2>
          <p className="text-sm text-muted">Read-only decision support with deterministic fallback and evidence IDs.</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      <section className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <article className="rounded-lg border border-line bg-white p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="rounded-md bg-teal-50 p-2 text-teal-700">
                <Bot className="h-5 w-5" />
              </span>
              <div>
                <h3 className="font-bold text-ink">Provider State</h3>
                <p className="text-xs text-muted">{health ? `${health.provider} · ${health.status}` : "Checking..."}</p>
              </div>
            </div>
            {health?.status === "DEGRADED" && (
              <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800">
                <ShieldAlert className="mr-2 inline h-4 w-4" />
                Model runtime unavailable; deterministic fallback is active.
              </div>
            )}
            <div className="mt-4 text-xs text-muted">
              {(models?.models ?? []).map((model: any) => (
                <p key={model.id} className="rounded-md bg-slate-50 px-2 py-1 font-mono">
                  {model.id} · {model.status}
                </p>
              ))}
            </div>
          </article>

          <article className="rounded-lg border border-line bg-white p-4 shadow-sm">
            <h3 className="mb-3 font-bold text-ink">Assistant Request</h3>
            <div className="space-y-3">
              <label className="grid gap-1 text-sm font-semibold text-ink">
                Operation
                <select value={operation} onChange={(event) => setOperation(event.target.value as Operation)} className="rounded-md border border-line bg-white px-3 py-2 text-sm focus:border-teal-500 focus:outline-none">
                  <option value="incident-priority">Incident priority</option>
                  <option value="dispatch-brief">Dispatch brief</option>
                  <option value="scenario-explanation">Scenario explanation</option>
                </select>
              </label>
              <label className="grid gap-1 text-sm font-semibold text-ink">
                Evidence Incident
                <select value={selectedIncident?.id ?? ""} onChange={(event) => setSelectedIncidentId(Number(event.target.value))} className="rounded-md border border-line bg-white px-3 py-2 text-sm focus:border-teal-500 focus:outline-none">
                  {incidents.map((incident) => (
                    <option key={incident.id} value={incident.id}>
                      #{incident.id} {incident.title}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={runAssistant}
                disabled={running || loading || !selectedIncident}
                className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-teal-700 disabled:opacity-60"
              >
                <BrainCircuit className="h-4 w-4" />
                {running ? "Generating..." : "Generate"}
              </button>
            </div>
          </article>
        </div>

        <article className="rounded-lg border border-line bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3 border-b border-line pb-4">
            <span className="rounded-md bg-indigo-50 p-2 text-indigo-700">
              <Lightbulb className="h-5 w-5" />
            </span>
            <div>
              <h3 className="font-bold text-ink">Assistant Output</h3>
              <p className="text-xs text-muted">Evidence-bound, read-only recommendations</p>
            </div>
          </div>

          {result ? (
            <div className="mt-4 space-y-4">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-sm font-bold text-ink">{result.summary}</p>
                <p className="mt-1 text-xs text-muted">Provider {result.provider} · Model {result.model} · Confidence {Math.round(result.confidence * 100)}%</p>
              </div>
              <div>
                <h4 className="text-sm font-bold text-ink">Recommendations</h4>
                <ul className="mt-2 space-y-2 text-sm text-muted">
                  {result.recommendations.map((item: string) => (
                    <li key={item} className="rounded-md border border-line bg-white px-3 py-2">{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-bold text-ink">Evidence</h4>
                <div className="mt-2 grid gap-2">
                  {result.evidence.map((item: any) => (
                    <div key={item.id} className="rounded-md bg-slate-50 p-3 text-xs">
                      <p className="font-mono font-bold text-ink">{item.id}</p>
                      <p className="mt-1 text-muted">{item.summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-8 flex min-h-[280px] items-center justify-center rounded-lg border border-dashed border-line bg-slate-50 text-sm text-muted">
              <ClipboardList className="mr-2 h-4 w-4" />
              Select evidence and generate a read-only assistant response.
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
