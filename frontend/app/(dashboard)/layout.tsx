"use client";

import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, BarChart3, Bot, Building2, ClipboardList, FileText, LayoutDashboard, LogOut, PlayCircle, RefreshCw, Route, Server, Truck, Wifi, WifiOff } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useIncidentEvents } from "@/hooks/useIncidentEvents";
import { RefreshProvider, useRefresh } from "@/context/RefreshContext";
import { useAuth } from "@/context/AuthContext";
import type { UserRole } from "@/lib/api";

type NavigationItem = { id: string; label: string; icon: any; href: string; roles?: UserRole[] };

const navigation: NavigationItem[] = [
  { id: "dashboard", label: "Overview", icon: LayoutDashboard, href: "/dashboard" },
  { id: "incidents", label: "Incidents", icon: ClipboardList, href: "/incidents" },
  { id: "vehicles", label: "Vehicles", icon: Truck, href: "/vehicles" },
  { id: "dispatches", label: "Dispatches", icon: Route, href: "/dispatches" },
  { id: "operations", label: "Operations", icon: Activity, href: "/operations" },
  { id: "simulations", label: "Simulation", icon: PlayCircle, href: "/simulations" },
  { id: "assistant", label: "Assistant", icon: Bot, href: "/assistant" },
  { id: "audit", label: "Audit", icon: FileText, href: "/audit", roles: ["ADMIN", "AUDITOR"] },
  { id: "analytics", label: "Analytics", icon: BarChart3, href: "/analytics" },
  { id: "system", label: "System", icon: Server, href: "/system" }
];

function StatusPill({ icon: Icon, label, tone }: { icon: any; label: string; tone: "good" | "warn" | "danger" }) {
  const toneClass = tone === "good" ? "bg-teal-50 text-teal-700" : tone === "warn" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-500";
  return (
    <span className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold ${toneClass}`}>
      <Icon className="h-4 w-4" /> {label}
    </span>
  );
}

function DashboardLayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isOnline = useOnlineStatus();
  const { refresh } = useRefresh();
  const { user, loading, logout, hasRole } = useAuth();
  
  // Realtime updates
  const incidentConnectionStatus = useIncidentEvents(refresh, Boolean(user));

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    router.replace("/login");
    return null;
  }

  const visibleNavigation = navigation.filter((item) => !item.roles || item.roles.some((role) => hasRole(role)));

  const activeItem = visibleNavigation.find(
    (item) => pathname.startsWith(item.href)
  ) || visibleNavigation[0];

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[260px_minmax(0,1fr)] bg-slate-50">
      <aside className="min-w-0 overflow-hidden border-b border-line bg-ink px-4 py-4 text-white lg:border-b-0 lg:border-r lg:border-white/10 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 px-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-500">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold">UrbanShield</h1>
              <p className="text-xs text-white/60">Operations console</p>
            </div>
          </div>
          
          <nav className="mt-6 flex w-full max-w-full gap-2 overflow-x-auto lg:flex-col lg:overflow-visible" aria-label="Workspace navigation">
            {visibleNavigation.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || (item.id !== "dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={`inline-flex min-w-max items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition lg:min-w-0 ${active ? "bg-white text-ink" : "text-white/72 hover:bg-white/10 hover:text-white"}`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        
        <div className="mt-6 hidden rounded-lg border border-white/10 bg-white/8 p-3 text-sm lg:block">
          <p className="font-semibold text-white">Simulation flow</p>
          <ol className="mt-3 space-y-2 text-white/68">
            <li>1. Set incident type and severity.</li>
            <li>2. Place the scenario on the map.</li>
            <li>3. Run and convert the result to an incident.</li>
          </ol>
        </div>
      </aside>

      <section className="min-w-0 flex flex-col">
        <header className="sticky top-0 z-20 border-b border-line bg-white/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Smart City Management</p>
              <h2 className="text-2xl font-bold text-ink">{activeItem?.label}</h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill icon={isOnline === false ? WifiOff : Wifi} label={isOnline === null ? "Checking network" : isOnline ? "Online" : "Offline"} tone={isOnline === false ? "danger" : "good"} />
              <StatusPill icon={Activity} label={`Events: ${incidentConnectionStatus}`} tone={incidentConnectionStatus === "connected" ? "good" : "warn"} />
              <span className="inline-flex items-center gap-2 rounded-md bg-slate-100 px-3 py-2 text-sm font-semibold text-ink">
                {user.displayName} · {user.role}
              </span>
              <button 
                type="button" 
                onClick={refresh} 
                className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50 transition"
              >
                <RefreshCw className="h-4 w-4" /> Refresh
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50"
              >
                <LogOut className="h-4 w-4" /> Logout
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1">
          {children}
        </main>
      </section>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RefreshProvider>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </RefreshProvider>
  );
}
