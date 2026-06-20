"use client";

import { useEffect, useState } from "react";
import { useRefresh } from "@/context/RefreshContext";
import { SystemSummary } from "@/components/SystemSummary";
import { fetchServiceHealth } from "@/lib/health";
import type { HealthState } from "@/lib/health";

export default function SystemPage() {
  const { refreshTrigger } = useRefresh();
  const [health, setHealth] = useState<HealthState[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkHealth() {
      try {
        setLoading(true);
        // Query health via gateway endpoints
        const [coreHealth, simHealth, aiHealth] = await Promise.all([
          fetchServiceHealth("/api/v1/system/core-health"),
          fetchServiceHealth("/simulation/api/simulation/health"),
          fetchServiceHealth("/api/v1/ai/health"),
        ]);
        
        // Match response names if they are empty
        const nextHealth: HealthState[] = [
          coreHealth.state === "up" ? coreHealth : ({ ...coreHealth, service: "core-api" } as HealthState),
          simHealth.state === "up" ? simHealth : ({ ...simHealth, service: "simulation-service" } as HealthState),
          aiHealth.state === "up" || aiHealth.state === "degraded" ? aiHealth : ({ ...aiHealth, service: "ai-service" } as HealthState),
        ];
        
        setHealth(nextHealth);
        setLastUpdated(new Date().toLocaleTimeString());
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    checkHealth();
  }, [refreshTrigger]);

  const servicesUp = health.filter((h) => h.state === "up").length;

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-ink">System Status Center</h2>
        <p className="text-sm text-muted">Inspect gateway health metrics, API routing states, and microservice status logs.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <SystemSummary
          totalServices={3}
          servicesUp={servicesUp}
          health={health}
          lastUpdated={lastUpdated}
        />
        <SystemEndpoints />
      </div>
    </div>
  );
}

function SystemEndpoints() {
  const endpoints = [
    ["Gateway Router", "http://127.0.0.1:8000", "Entry point for all UI and service traffic"],
    ["Frontend Console", "http://localhost:3000", "Next.js Smart City User Interface"],
    ["Core Telemetry API", "http://127.0.0.1:8000/api/v1/system/core-health", "Gateway-routed database operations"],
    ["Simulation Service", "http://127.0.0.1:8000/simulation/api/simulation/health", "Gateway-routed deterministic engine"],
    ["AI Service", "http://127.0.0.1:8000/api/v1/ai/health", "Fallback assistant and evidence summaries"]
  ];

  return (
    <section className="bg-white rounded-xl border border-line p-5 shadow-sm space-y-4">
      <h2 className="text-lg font-bold text-ink">Active Microservice Endpoints</h2>
      <div className="divide-y divide-line">
        {endpoints.map(([label, url, desc]) => (
          <div key={label} className="grid gap-1.5 py-4.5 first:pt-0 last:pb-0 sm:grid-cols-[160px_minmax(0,1fr)] text-sm">
            <div>
              <p className="font-bold text-ink">{label}</p>
              <p className="text-xs text-muted mt-0.5">{desc}</p>
            </div>
            <p className="break-all font-mono text-xs text-teal-700 bg-slate-50 border border-line p-2.5 rounded-lg select-all max-w-lg self-center">
              {url}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
