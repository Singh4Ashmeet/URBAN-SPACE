"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, FileText, Inbox, RefreshCw, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { fetchAuditLog, fetchOutboxStatus } from "@/lib/api";

export default function AuditPage() {
  const { canAudit } = useAuth();
  const [logs, setLogs] = useState<any[]>([]);
  const [outbox, setOutbox] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadAudit() {
    if (!canAudit) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [auditRes, outboxRes] = await Promise.all([fetchAuditLog(), fetchOutboxStatus()]);
      setLogs(auditRes.content);
      setOutbox(outboxRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit request failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAudit();
  }, [canAudit]);

  if (!canAudit) {
    return (
      <div className="p-4 sm:p-6">
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-900">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5" />
            <h2 className="text-lg font-bold">Audit Access Restricted</h2>
          </div>
          <p className="mt-2 text-sm font-medium">Your current role cannot inspect audit or outbox records.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-ink">Audit & Outbox Ledger</h2>
          <p className="text-sm text-muted">Role-protected system actions, authorization events, and pending integration events.</p>
        </div>
        <button
          type="button"
          onClick={loadAudit}
          className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">
          {error}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-3">
        <Metric icon={FileText} label="Audit Records" value={loading ? "..." : String(logs.length)} />
        <Metric icon={Inbox} label="Pending Outbox" value={outbox ? String(outbox.pending ?? outbox.pendingEvents ?? 0) : "..."} />
        <Metric icon={ShieldCheck} label="Access Mode" value="Protected" />
      </section>

      <section className="rounded-lg border border-line bg-white shadow-sm">
        <div className="border-b border-line px-4 py-3">
          <h3 className="text-base font-bold text-ink">Recent Audit Events</h3>
        </div>
        <div className="max-h-[620px] overflow-auto">
          {logs.map((log) => (
            <article key={log.id} className="grid gap-2 border-b border-line px-4 py-3 last:border-b-0 lg:grid-cols-[180px_190px_minmax(0,1fr)]">
              <div>
                <p className="text-xs font-bold uppercase text-muted">{log.action}</p>
                <p className="mt-1 text-xs text-muted">{new Date(log.timestamp).toLocaleString()}</p>
              </div>
              <div className="text-sm">
                <p className="font-semibold text-ink">{log.resource_type}</p>
                <p className="text-xs text-muted">ID {log.resource_id ?? "n/a"}</p>
              </div>
              <p className="break-words rounded-md bg-slate-50 p-2 font-mono text-xs text-muted">{log.details}</p>
            </article>
          ))}
          {!loading && logs.length === 0 && <p className="p-6 text-center text-sm text-muted">No audit events recorded.</p>}
        </div>
      </section>
    </div>
  );
}

function Metric({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <article className="rounded-lg border border-line bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-muted">{label}</p>
        <span className="rounded-md bg-teal-50 p-2 text-teal-700">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold text-ink">{value}</p>
    </article>
  );
}
