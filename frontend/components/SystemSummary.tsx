import { ShieldCheck } from "lucide-react";
import type { HealthState } from "@/lib/health";

type SystemSummaryProps = {
  totalServices: number;
  servicesUp: number;
  health: HealthState[];
  lastUpdated: string | null;
};

export function SystemSummary({ totalServices, servicesUp, health, lastUpdated }: SystemSummaryProps) {
  const hasLoading = health.some((service) => service.state === "loading");
  const hasDown = health.some((service) => service.state === "down");
  const hasDegraded = health.some((service) => service.state === "degraded");

  const status = hasLoading
    ? "Checking services"
    : hasDown
      ? "System failure"
      : hasDegraded
        ? "System degraded"
        : "All systems operational";

  return (
    <aside className="rounded-lg border border-line bg-ink p-5 text-white shadow-soft sm:p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-md bg-teal-500 text-white">
          <ShieldCheck className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-xl font-semibold">{status}</h2>
          <p className="mt-1 text-sm text-white/70">Combined status summary</p>
        </div>
      </div>

      <div className="mt-7 grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-white/10 bg-white/10 p-4">
          <p className="text-3xl font-bold">{servicesUp}</p>
          <p className="mt-1 text-sm text-white/70">Services up</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/10 p-4">
          <p className="text-3xl font-bold">{totalServices}</p>
          <p className="mt-1 text-sm text-white/70">Tracked services</p>
        </div>
      </div>

      <p className="mt-6 text-sm leading-6 text-white/75">
        Traffic enters through the local gateway at port 8000, then routes to the core incident API and simulation API.
      </p>
      <p className="mt-4 text-xs font-medium text-white/55">
        Last refreshed: {lastUpdated ?? "Waiting for first check"}
      </p>
    </aside>
  );
}
