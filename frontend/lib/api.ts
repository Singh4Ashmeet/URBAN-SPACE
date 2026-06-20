import type { Incident, IncidentFilters, IncidentSummary } from "@/types/incidents";
import type { DispatchRecord, DispatchRequest, DispatchResponse, EmergencyVehicle, VehiclePageResponse, VehicleStatus, VehicleType } from "@/types/allocation";
import type { SimulationRequest, SimulationResponse } from "@/types/simulation";

export type UserRole = "ADMIN" | "OPERATOR" | "AUDITOR" | "VIEWER";

export type AuthUser = {
  id: number;
  username: string;
  displayName: string;
  role: UserRole;
};

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  user: AuthUser;
};

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const GATEWAY_BASE_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
export const CORE_API_BASE_URL = API_BASE_URL;
export const SIMULATION_API_BASE_URL = API_BASE_URL;
export const SIMULATION_WS_URL = process.env.NEXT_PUBLIC_SIMULATION_WS_URL ?? "ws://127.0.0.1:8000/api/v1/simulations/progress";

type PageResponse<T> = {
  content: T[];
  totalElements?: number;
};

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export function getAccessToken(): string | null {
  return storage()?.getItem("urbanshield.accessToken") ?? null;
}

export function getRefreshToken(): string | null {
  return storage()?.getItem("urbanshield.refreshToken") ?? null;
}

export function getStoredUser(): AuthUser | null {
  const value = storage()?.getItem("urbanshield.user");
  if (!value) return null;
  try {
    return JSON.parse(value) as AuthUser;
  } catch {
    return null;
  }
}

export function setAuthSession(session: AuthSession) {
  const target = storage();
  target?.setItem("urbanshield.accessToken", session.accessToken);
  target?.setItem("urbanshield.refreshToken", session.refreshToken);
  target?.setItem("urbanshield.expiresAt", session.expiresAt);
  target?.setItem("urbanshield.user", JSON.stringify(session.user));
}

export function clearAuthSession() {
  const target = storage();
  target?.removeItem("urbanshield.accessToken");
  target?.removeItem("urbanshield.refreshToken");
  target?.removeItem("urbanshield.expiresAt");
  target?.removeItem("urbanshield.user");
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken }),
    cache: "no-store"
  });
  if (!response.ok) {
    clearAuthSession();
    return false;
  }
  setAuthSession((await response.json()) as AuthSession);
  return true;
}

async function request<T>(path: string, init?: RequestInit, retry = true): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (response.status === 401 && retry && await refreshAccessToken()) {
    return request<T>(path, init, false);
  }
  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || body.error || message;
    } catch {
      // Keep status message.
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function login(username: string, password: string): Promise<AuthSession> {
  const session = await request<AuthSession>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  }, false);
  setAuthSession(session);
  return session;
}

export async function logout(): Promise<void> {
  try {
    await request<{ status: string }>("/auth/logout", { method: "POST" }, false);
  } finally {
    clearAuthSession();
  }
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
}

export function incidentEventsUrl(): string {
  const token = getAccessToken();
  const suffix = token ? `?access_token=${encodeURIComponent(token)}` : "";
  return `${API_BASE_URL}/incidents/events${suffix}`;
}

export async function fetchIncidents(filters: Partial<IncidentFilters> = {}): Promise<Incident[]> {
  const params = new URLSearchParams({ size: "100", sortBy: "reportedAt", direction: "desc" });
  if (filters.status) params.set("status", filters.status);
  if (filters.incidentType) params.set("incidentType", filters.incidentType);
  if (filters.minimumSeverity) params.set("minimumSeverity", filters.minimumSeverity);
  const page = await request<PageResponse<Incident>>(`/incidents?${params.toString()}`);
  return page.content;
}

export async function fetchIncidentSummary(): Promise<IncidentSummary> {
  return request<IncidentSummary>("/incidents/summary");
}

export async function createIncident(payload: Omit<Incident, "id" | "reportedAt" | "updatedAt">): Promise<Incident> {
  return request<Incident>("/incidents", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateIncidentStatus(id: number, status: string, version?: number): Promise<Incident> {
  return request<Incident>(`/incidents/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, version }) });
}

export async function deleteIncident(id: number): Promise<void> {
  await request<void>(`/incidents/${id}`, { method: "DELETE" });
}

export async function runScenario(payload: SimulationRequest): Promise<SimulationResponse> {
  return request<SimulationResponse>("/simulations/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function fetchSimulationRuns(): Promise<PageResponse<SimulationResponse>> {
  return request<PageResponse<SimulationResponse>>("/simulations/runs");
}

export async function compareSimulationRuns(runIds: number[]) {
  return request<any>("/simulations/compare", { method: "POST", body: JSON.stringify({ runIds }) });
}

export function simulationExportUrl(runId: number, format: "json" | "csv") {
  return `${API_BASE_URL}/simulations/runs/${runId}/export?format=${format}`;
}

export async function downloadSimulationExport(runId: number, format: "json" | "csv"): Promise<Blob> {
  const response = await fetch(simulationExportUrl(runId, format), {
    headers: authHeaders(),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Export failed with HTTP ${response.status}`);
  }
  return response.blob();
}

export async function fetchVehicles(filters: { status?: VehicleStatus; vehicleType?: VehicleType } = {}): Promise<VehiclePageResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.vehicleType) params.set("vehicleType", filters.vehicleType);
  const query = params.toString();
  return request<VehiclePageResponse>(`/vehicles${query ? `?${query}` : ""}`);
}

export async function fetchNearbyVehicles(latitude: number, longitude: number, radiusMeters: number): Promise<EmergencyVehicle[]> {
  const params = new URLSearchParams({ latitude: String(latitude), longitude: String(longitude), radiusMeters: String(radiusMeters) });
  return request<EmergencyVehicle[]>(`/vehicles/nearby?${params.toString()}`);
}

export async function fetchVehicleRecommendations(incidentId: number, vehicleType?: VehicleType): Promise<any[]> {
  const params = new URLSearchParams({ incidentId: String(incidentId) });
  if (vehicleType) params.set("vehicleType", vehicleType);
  return request<any[]>(`/dispatch/recommend?${params.toString()}`);
}

export async function createDispatch(payload: DispatchRequest): Promise<DispatchResponse> {
  return request<DispatchResponse>("/dispatch", { method: "POST", body: JSON.stringify(payload) });
}

export async function fetchDispatches(): Promise<{ content: DispatchRecord[]; totalElements: number }> {
  return request<{ content: DispatchRecord[]; totalElements: number }>("/dispatches");
}

export async function fetchIncidentById(id: number): Promise<Incident> {
  return request<Incident>(`/incidents/${id}`);
}

export async function fetchIncidentHistory(id: number): Promise<any[]> {
  return request<any[]>(`/incidents/${id}/history`);
}

export async function createVehicle(payload: any): Promise<EmergencyVehicle> {
  return request<EmergencyVehicle>("/vehicles", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateVehicleStatus(id: number, status: string, version?: number): Promise<any> {
  return request<any>(`/vehicles/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, version }) });
}

export async function updateVehicleLocation(id: number, latitude: number, longitude: number, version?: number): Promise<any> {
  return request<any>(`/vehicles/${id}/location`, { method: "PATCH", body: JSON.stringify({ latitude, longitude, version }) });
}

export async function deleteVehicle(id: number): Promise<void> {
  await request<void>(`/vehicles/${id}`, { method: "DELETE" });
}

export async function updateDispatchStatus(id: number, status: string): Promise<any> {
  return request<any>(`/dispatches/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
}

export async function fetchAuditLog(): Promise<{ content: any[]; totalElements: number }> {
  return request<{ content: any[]; totalElements: number }>("/audit");
}

export async function fetchOutboxStatus(): Promise<any> {
  return request<any>("/outbox");
}

export async function fetchAiHealth(): Promise<any> {
  return request<any>("/ai/health");
}

export async function fetchAiModels(): Promise<any> {
  return request<any>("/ai/models");
}

export async function requestAi(operation: "incident-priority" | "dispatch-brief" | "scenario-explanation", payload: any): Promise<any> {
  return request<any>(`/ai/${operation}`, { method: "POST", body: JSON.stringify(payload) });
}

export { GATEWAY_BASE_URL };
