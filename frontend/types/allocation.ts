export type VehicleType = "AMBULANCE" | "FIRE_ENGINE" | "POLICE_CAR" | "RESCUE_VEHICLE" | "MOBILE_COMMAND_UNIT";

export type VehicleStatus = "AVAILABLE" | "RESERVED" | "DISPATCHED" | "EN_ROUTE" | "ON_SCENE" | "RETURNING" | "OUT_OF_SERVICE";

export type EmergencyVehicle = {
  id: number;
  callSign: string;
  vehicleType: VehicleType;
  status: VehicleStatus;
  latitude: number;
  longitude: number;
  capacity: number;
  maximumSpeedKph: number;
  homeStation?: string | null;
  assignedIncidentId?: number | null;
  lastSeenAt?: string;
  version?: number;
  distanceKm?: number;
};

export type VehiclePageResponse = {
  content: EmergencyVehicle[];
  totalElements: number;
};

export type DispatchRequest = {
  incidentId: number;
  requestedVehicleCount: number;
  priority: number;
  vehicleType?: VehicleType;
};

export type DispatchAssignment = {
  dispatchId: number;
  vehicle: EmergencyVehicle;
  distanceKm: number;
  estimatedArrivalMinutes: number;
};

export type DispatchResponse = {
  incidentId: number;
  assignments: DispatchAssignment[];
  warnings: string[];
};

export type DispatchRecord = {
  id: number;
  incident_id: number;
  vehicle_id: number;
  status: string;
  priority: number;
  distance_km: number;
  estimated_arrival_minutes: number;
  assignment_reason: string;
  dispatched_at: string;
  created_at: string;
  updated_at: string;
};
