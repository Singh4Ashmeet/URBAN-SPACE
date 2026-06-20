import type { IncidentType } from "./incidents";

export type TrafficLevel = "LOW" | "MODERATE" | "HIGH" | "SEVERE";
export type WeatherCondition = "CLEAR" | "RAIN" | "HEAVY_RAIN" | "FOG" | "STORM";

export type SimulationRequest = {
  scenario_name: string;
  incident_type: IncidentType;
  severity: number;
  latitude: number;
  longitude: number;
  number_of_vehicles: number;
  traffic_level: TrafficLevel;
  weather_condition: WeatherCondition;
  road_blocked: boolean;
  simulation_duration_minutes: number;
};

export type SimulationResponse = {
  id?: number;
  runId?: number;
  scenarioId?: number;
  simulation_id: string;
  scenario_name: string;
  incident_type: IncidentType;
  severity: number;
  estimated_response_time_minutes: number;
  estimated_affected_radius_meters: number;
  recommended_vehicle_count: number;
  risk_score: number;
  route_distance_km: number;
  warnings: string[];
  status: string;
  simulation_version?: string;
  input_hash?: string;
  seed?: number;
  duration_ms?: number;
  started_at: string;
  completed_at: string;
};
