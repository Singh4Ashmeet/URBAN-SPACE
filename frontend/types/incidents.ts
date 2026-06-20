export type IncidentType =
  | "ACCIDENT"
  | "FIRE"
  | "FLOOD"
  | "ROAD_CLOSURE"
  | "TRAFFIC_JAM"
  | "MEDICAL_EMERGENCY"
  | "PUBLIC_HAZARD";

export type IncidentStatus = "REPORTED" | "VERIFIED" | "DISPATCHED" | "IN_PROGRESS" | "RESOLVED" | "CANCELLED";

export type Incident = {
  id: number;
  title: string;
  description?: string | null;
  incidentType: IncidentType;
  severity: number;
  status: IncidentStatus;
  latitude: number;
  longitude: number;
  reportedAt?: string;
  updatedAt?: string;
  resolvedAt?: string | null;
  district?: string | null;
  version?: number;
};

export type IncidentSummary = {
  totalIncidents: number;
  activeIncidents: number;
  resolvedIncidents: number;
  byType: Record<string, number>;
  byStatus: Record<string, number>;
  bySeverity: Record<string, number>;
  averageSeverity: number;
};

export type IncidentFilters = {
  incidentType: string;
  status: string;
  minimumSeverity: string;
};
