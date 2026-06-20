import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { HealthState } from "@/lib/health";

type StatusCardProps = {
  title: string;
  description: string;
  health: HealthState;
};

const statusStyles = {
  loading: {
    label: "Checking",
    className: "border-amber-500 bg-amber-50 text-amber-500",
    icon: Loader2
  },
  up: {
    label: "UP",
    className: "border-teal-500 bg-teal-50 text-teal-700",
    icon: CheckCircle2
  },
  degraded: {
    label: "Degraded",
    className: "border-amber-500 bg-amber-50 text-amber-500",
    icon: AlertTriangle
  },
  down: {
    label: "Unavailable",
    className: "border-danger-500 bg-danger-50 text-danger-500",
    icon: XCircle
  }
} as const;

export function StatusCard({ title, description, health }: StatusCardProps) {
  const style = statusStyles[health.state];
  const Icon = style.icon;

  return (
    <article className="min-h-44 rounded-lg border border-line bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-ink">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
        </div>
        <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-bold ${style.className}`}>
          <Icon className={health.state === "loading" ? "h-4 w-4 animate-spin" : "h-4 w-4"} aria-hidden="true" />
          {style.label}
        </span>
      </div>
      <dl className="mt-5 grid gap-3 text-sm">
        <div className="flex justify-between gap-3 border-t border-line pt-3">
          <dt className="text-muted">Service response</dt>
          <dd className="font-medium text-ink">{health.service ?? "Pending"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Details</dt>
          <dd className="text-right font-medium text-ink">{health.message}</dd>
        </div>
      </dl>
    </article>
  );
}
