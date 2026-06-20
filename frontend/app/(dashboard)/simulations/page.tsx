"use client";

import { useEffect, useState } from "react";
import { Download, GitCompare, PlayCircle } from "lucide-react";
import { runScenario, createIncident, fetchSimulationRuns, compareSimulationRuns, downloadSimulationExport } from "@/lib/api";
import { useRefresh } from "@/context/RefreshContext";
import { useAuth } from "@/context/AuthContext";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useSimulationProgress } from "@/hooks/useSimulationProgress";
import { queueDraftScenario } from "@/lib/offline";
import { ScenarioBuilder, defaultScenario } from "@/components/scenario/ScenarioBuilder";
import { CityMap } from "@/components/map/CityMap";
import type { SimulationResponse } from "@/types/simulation";

export default function SimulationsPage() {
  const { refresh } = useRefresh();
  const { canMutate } = useAuth();
  const [scenario, setScenario] = useState(defaultScenario());
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null);
  const [runs, setRuns] = useState<SimulationResponse[]>([]);
  const [selectedRunIds, setSelectedRunIds] = useState<number[]>([]);
  const [comparison, setComparison] = useState<any | null>(null);
  const [statusMessage, setStatusMessage] = useState("Configure parameters and click 'Run simulation'.");
  const isOnline = useOnlineStatus();
  const { events, status: simulationConnectionStatus, startProgress } = useSimulationProgress();

  async function loadRuns() {
    const response = await fetchSimulationRuns();
    setRuns(response.content);
  }

  useEffect(() => {
    loadRuns().catch(() => {});
  }, []);

  const handleRunScenario = async () => {
    if (!canMutate) {
      setStatusMessage("Current role cannot run or persist simulations.");
      return;
    }
    startProgress();
    if (isOnline === false) {
      await queueDraftScenario(scenario);
      setStatusMessage("Scenario draft queued locally (Offline mode).");
      return;
    }
    try {
      setStatusMessage("Executing simulation model on backend...");
      const result = await runScenario(scenario);
      setSimulationResult(result);
      setStatusMessage("Simulation completed successfully.");
      await loadRuns();
      refresh();
    } catch (err) {
      console.error(err);
      await queueDraftScenario(scenario);
      setStatusMessage("Simulation service unavailable. Draft queued locally.");
    }
  };

  const handleCreateIncident = async () => {
    if (!simulationResult) return;
    if (!canMutate) {
      setStatusMessage("Current role cannot convert simulation results to incidents.");
      return;
    }
    try {
      await createIncident({
        title: simulationResult.scenario_name,
        description: `Generated from a completed simulation scenario (${simulationResult.simulation_id}).`,
        incidentType: simulationResult.incident_type,
        severity: simulationResult.severity,
        status: "REPORTED",
        latitude: scenario.latitude,
        longitude: scenario.longitude
      });
      setStatusMessage("Incident created from simulation results.");
      refresh();
    } catch (err) {
      console.error(err);
      setStatusMessage("Failed to convert simulation to incident.");
    }
  };

  const handleCompare = async () => {
    if (selectedRunIds.length < 2) return;
    setComparison(await compareSimulationRuns(selectedRunIds));
  };

  const handleExport = async (runId: number, format: "json" | "csv") => {
    const blob = await downloadSimulationExport(runId, format);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `urbanshield-simulation-${runId}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const toggleRun = (runId?: number) => {
    if (!runId) return;
    setSelectedRunIds((current) =>
      current.includes(runId)
        ? current.filter((item) => item !== runId)
        : current.length >= 4
          ? [...current.slice(1), runId]
          : [...current, runId]
    );
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">Smart City Simulation Lab</h2>
          <p className="text-sm text-muted">Model incident severity effects on response times and route options.</p>
        </div>
      </div>

      <section className="bg-white p-3.5 rounded-xl border border-line shadow-sm flex justify-between items-center text-sm font-semibold text-ink">
        <span>{statusMessage}</span>
        <span className="text-muted text-xs">Engine: Local Subprocess</span>
      </section>

      <div className="grid gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">
        {/* Left Column: Builder Controls */}
        <div className="space-y-6">
          <ScenarioBuilder
            value={scenario}
            onChange={setScenario}
            onRun={handleRunScenario}
            onSaveDraft={() => queueDraftScenario(scenario)}
            isRunning={simulationConnectionStatus === "connected"}
            progressEvents={events}
            result={simulationResult}
          />
        </div>

        {/* Right Column: Coordinate Map & Live Results */}
        <div className="space-y-6">
          <div className="bg-white p-4 rounded-xl border border-line shadow-sm space-y-3">
            <h3 className="font-bold text-ink text-base">Select Telemetry Coordinates</h3>
            <p className="text-xs text-muted">Click on the map to place the simulation coordinates.</p>
            <div className="h-[320px] rounded-lg overflow-hidden border border-line">
              <CityMap
                incidents={[]}
                selectedIncident={null}
                onSelectIncident={() => {}}
                is3d={false}
                scenarioPoint={{ latitude: scenario.latitude, longitude: scenario.longitude }}
                onPlaceScenario={(point) => setScenario((current) => ({ ...current, ...point }))}
                vehicles={[]}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="border border-line rounded-lg p-2.5 bg-slate-50 text-xs">
                <span className="text-muted block uppercase font-bold">Latitude</span>
                <span className="font-bold text-ink text-sm">{scenario.latitude.toFixed(5)}</span>
              </div>
              <div className="border border-line rounded-lg p-2.5 bg-slate-50 text-xs">
                <span className="text-muted block uppercase font-bold">Longitude</span>
                <span className="font-bold text-ink text-sm">{scenario.longitude.toFixed(5)}</span>
              </div>
            </div>
          </div>

          {simulationResult && (
            <div className="bg-white p-5 rounded-xl border border-line shadow-sm space-y-4">
              <div className="flex justify-between items-center">
                <h4 className="font-bold text-ink text-base">Model Outputs Explainer</h4>
                <button
                  type="button"
                  onClick={handleCreateIncident}
                  disabled={!canMutate}
                  className="rounded-lg bg-teal-600 hover:bg-teal-700 px-4 py-2 text-xs font-bold text-white transition disabled:opacity-50"
                >
                  Convert to Live Incident
                </button>
              </div>
              <p className="text-sm text-muted leading-relaxed">
                Our smart city routing engine computes these results based on a severity score of {simulationResult.severity}/5 with a traffic multiplier of {scenario.traffic_level} and weather status of {scenario.weather_condition}.
              </p>
              <div className="grid gap-3 sm:grid-cols-4 text-xs font-semibold">
                <div className="border border-line rounded-lg p-3 bg-slate-50">
                  <span className="text-muted block uppercase">Risk Index</span>
                  <span className="font-bold text-ink text-lg">{simulationResult.risk_score}/100</span>
                </div>
                <div className="border border-line rounded-lg p-3 bg-slate-50">
                  <span className="text-muted block uppercase">Est. Response Time</span>
                  <span className="font-bold text-ink text-lg">{simulationResult.estimated_response_time_minutes} mins</span>
                </div>
                <div className="border border-line rounded-lg p-3 bg-slate-50">
                  <span className="text-muted block uppercase">Affected Area</span>
                  <span className="font-bold text-ink text-lg">{simulationResult.estimated_affected_radius_meters} meters</span>
                </div>
                <div className="border border-line rounded-lg p-3 bg-slate-50">
                  <span className="text-muted block uppercase">Rec. Units</span>
                  <span className="font-bold text-ink text-lg">{simulationResult.recommended_vehicle_count} vehicles</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="rounded-xl border border-line bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
            <div>
              <h3 className="font-bold text-ink">Persisted Simulation Runs</h3>
              <p className="text-xs text-muted">Rule version, input hash, seed, and exported run evidence.</p>
            </div>
            <button
              type="button"
              onClick={handleCompare}
              disabled={selectedRunIds.length < 2}
              className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-bold text-ink transition hover:bg-slate-50 disabled:opacity-50"
            >
              <GitCompare className="h-4 w-4" /> Compare
            </button>
          </div>
          <div className="mt-3 max-h-[420px] overflow-auto">
            {runs.map((run) => (
              <article key={run.runId ?? run.id ?? run.simulation_id} className="grid gap-3 border-b border-line py-3 last:border-b-0 lg:grid-cols-[28px_minmax(0,1fr)_180px]">
                <input
                  type="checkbox"
                  checked={Boolean(run.runId && selectedRunIds.includes(run.runId))}
                  onChange={() => toggleRun(run.runId)}
                  className="mt-1 h-4 w-4"
                  aria-label={`Select run ${run.runId}`}
                />
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-ink">{run.scenario_name}</p>
                  <p className="mt-1 font-mono text-[11px] text-muted">hash {run.input_hash ?? "n/a"} · seed {run.seed ?? "n/a"}</p>
                  <p className="mt-1 text-xs text-muted">
                    Risk {run.risk_score}/100 · ETA {run.estimated_response_time_minutes} min · version {run.simulation_version ?? "1.0.0"}
                  </p>
                </div>
                <div className="flex flex-wrap items-start gap-2 lg:justify-end">
                  {run.runId && (
                    <>
                      <button type="button" onClick={() => handleExport(run.runId!, "json")} className="inline-flex items-center gap-1 rounded border border-line px-2 py-1 text-xs font-bold text-ink hover:bg-slate-50">
                        <Download className="h-3.5 w-3.5" /> JSON
                      </button>
                      <button type="button" onClick={() => handleExport(run.runId!, "csv")} className="inline-flex items-center gap-1 rounded border border-line px-2 py-1 text-xs font-bold text-ink hover:bg-slate-50">
                        <Download className="h-3.5 w-3.5" /> CSV
                      </button>
                    </>
                  )}
                </div>
              </article>
            ))}
            {runs.length === 0 && <p className="py-6 text-center text-sm text-muted">No persisted runs yet.</p>}
          </div>
        </div>

        <div className="rounded-xl border border-line bg-white p-5 shadow-sm">
          <h3 className="font-bold text-ink">Comparison</h3>
          {comparison ? (
            <div className="mt-4 space-y-3">
              <p className="text-xs text-muted">Baseline run #{comparison.baselineRunId}</p>
              {comparison.deltas.map((delta: any) => (
                <div key={delta.runId} className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-bold text-ink">Run #{delta.runId}</p>
                  <p className="mt-1 text-xs text-muted">Risk delta {delta.riskScoreDelta} · ETA delta {delta.responseTimeDelta} · Radius delta {delta.affectedRadiusDelta}m</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted">Select two to four runs and compare deterministic deltas.</p>
          )}
        </div>
      </section>
    </div>
  );
}
