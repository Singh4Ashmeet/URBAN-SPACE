"use client";

import { useEffect, useState, useCallback } from "react";
import { PlusCircle, RefreshCw, Truck, MapPin, Trash2, Edit2, ShieldAlert } from "lucide-react";
import { useRefresh } from "@/context/RefreshContext";
import { useAuth } from "@/context/AuthContext";
import { fetchVehicles, createVehicle, updateVehicleStatus, updateVehicleLocation, deleteVehicle } from "@/lib/api";
import type { EmergencyVehicle, VehicleStatus, VehicleType } from "@/types/allocation";

export default function VehiclesPage() {
  const { refreshTrigger, refresh } = useRefresh();
  const { canMutate } = useAuth();
  const [vehicles, setVehicles] = useState<EmergencyVehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedVehicle, setSelectedVehicle] = useState<EmergencyVehicle | null>(null);

  // Filters state
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("");

  // Creation form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [callSign, setCallSign] = useState("");
  const [type, setType] = useState("AMBULANCE");
  const [capacity, setCapacity] = useState(4);
  const [maxSpeed, setMaxSpeed] = useState(70);
  const [homeStation, setHomeStation] = useState("");
  const [lat, setLat] = useState(28.6139);
  const [lng, setLng] = useState(77.2090);

  // Update states
  const [updatingLocation, setUpdatingLocation] = useState(false);
  const [upLat, setUpLat] = useState(28.6139);
  const [upLng, setUpLng] = useState(77.2090);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchVehicles({
        status: filterStatus ? (filterStatus as VehicleStatus) : undefined,
        vehicleType: filterType ? (filterType as VehicleType) : undefined,
      });
      setVehicles(res.content);
      // Keep selected vehicle reference updated
      if (selectedVehicle) {
        const updated = res.content.find((v) => v.id === selectedVehicle.id);
        setSelectedVehicle(updated || null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterType, selectedVehicle]);

  useEffect(() => {
    loadData();
  }, [refreshTrigger, filterStatus, filterType]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await createVehicle({
        callSign,
        vehicleType: type,
        status: "AVAILABLE",
        capacity,
        maximumSpeedKph: maxSpeed,
        homeStation: homeStation || null,
        latitude: lat,
        longitude: lng,
      });
      setShowCreateForm(false);
      setCallSign("");
      setHomeStation("");
      setSelectedVehicle(created);
      refresh();
    } catch (err) {
      console.error(err);
      alert("Error creating vehicle. Make sure the call sign is unique.");
    }
  };

  const handleStatusUpdate = async (id: number, status: string, version?: number) => {
    if (!canMutate) return;
    try {
      await updateVehicleStatus(id, status, version);
      refresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleLocationUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVehicle) return;
    if (!canMutate) return;
    try {
      await updateVehicleLocation(selectedVehicle.id, upLat, upLng, selectedVehicle.version);
      setUpdatingLocation(false);
      refresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (v: EmergencyVehicle) => {
    if (!canMutate) return;
    if (window.confirm(`Are you sure you want to delete emergency vehicle ${v.callSign}?`)) {
      try {
        await deleteVehicle(v.id);
        setSelectedVehicle(null);
        refresh();
      } catch (err) {
        console.error(err);
      }
    }
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">Emergency Fleet Management</h2>
          <p className="text-sm text-muted">Register, track, and locate ambulance, rescue, and police units.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateForm(!showCreateForm)}
          disabled={!canMutate}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 hover:bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white transition disabled:opacity-50"
        >
          <PlusCircle className="h-4 w-4" /> {showCreateForm ? "Cancel Creation" : "Register Vehicle"}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreate} className="bg-white p-5 rounded-xl border border-line shadow-sm max-w-xl space-y-4">
          <h3 className="font-bold text-ink text-base">Register Emergency Vehicle</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Call Sign
              <input
                type="text"
                required
                value={callSign}
                onChange={(e) => setCallSign(e.target.value)}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
                placeholder="AMB-25..."
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Vehicle Type
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              >
                {["AMBULANCE", "FIRE_ENGINE", "POLICE_CAR", "RESCUE_VEHICLE", "MOBILE_COMMAND_UNIT"].map((t) => (
                  <option key={t} value={t}>{t.replace("_", " ")}</option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Capacity
              <input
                type="number"
                min="1"
                max="50"
                value={capacity}
                onChange={(e) => setCapacity(Number(e.target.value))}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Max Speed (kph)
              <input
                type="number"
                min="1"
                value={maxSpeed}
                onChange={(e) => setMaxSpeed(Number(e.target.value))}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Home Station
              <input
                type="text"
                value={homeStation}
                onChange={(e) => setHomeStation(e.target.value)}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
                placeholder="Main Station..."
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Latitude
              <input
                type="number"
                step="0.0001"
                value={lat}
                onChange={(e) => setLat(Number(e.target.value))}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-ink">
              Longitude
              <input
                type="number"
                step="0.0001"
                value={lng}
                onChange={(e) => setLng(Number(e.target.value))}
                className="rounded-md border border-line px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
              />
            </label>
          </div>
          <button
            type="submit"
            className="w-full rounded-lg bg-teal-600 hover:bg-teal-700 py-2.5 text-sm font-bold text-white transition"
          >
            Add Vehicle to Fleet
          </button>
        </form>
      )}

      {/* Filter and List Section */}
      <div className="grid gap-6 md:grid-cols-[1fr_360px]">
        {/* Left Column: Fleet List */}
        <div className="bg-white rounded-xl border border-line shadow-sm p-4 space-y-4">
          <div className="flex flex-wrap items-center gap-4 border-b border-line pb-4">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="rounded-md border border-line px-3 py-2 text-sm focus:outline-none focus:border-teal-500 bg-white"
            >
              <option value="">All Types</option>
              {["AMBULANCE", "FIRE_ENGINE", "POLICE_CAR", "RESCUE_VEHICLE", "MOBILE_COMMAND_UNIT"].map((t) => (
                <option key={t} value={t}>{t.replace("_", " ")}</option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded-md border border-line px-3 py-2 text-sm focus:outline-none focus:border-teal-500 bg-white"
            >
              <option value="">All Statuses</option>
              {["AVAILABLE", "RESERVED", "DISPATCHED", "EN_ROUTE", "ON_SCENE", "RETURNING", "OUT_OF_SERVICE"].map((s) => (
                <option key={s} value={s}>{s.replace("_", " ")}</option>
              ))}
            </select>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 overflow-auto max-h-[550px] pr-1">
            {vehicles.map((v) => (
              <article
                key={v.id}
                onClick={() => {
                  setSelectedVehicle(v);
                  setUpLat(v.latitude);
                  setUpLng(v.longitude);
                  setUpdatingLocation(false);
                }}
                className={`rounded-xl border p-4 cursor-pointer hover:shadow-md transition flex items-start gap-3.5 ${
                  selectedVehicle?.id === v.id ? "border-teal-500 bg-teal-50" : "border-line bg-white"
                }`}
              >
                <span className={`p-2.5 rounded-lg ${
                  v.status === "AVAILABLE" ? "bg-teal-50 text-teal-700" : "bg-slate-100 text-ink"
                }`}>
                  <Truck className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <h4 className="font-bold text-ink text-base">{v.callSign}</h4>
                  <p className="text-xs text-muted font-medium">{v.vehicleType.replace("_", " ")}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      v.status === "AVAILABLE" ? "bg-teal-100 text-teal-800" :
                      v.status === "OUT_OF_SERVICE" ? "bg-red-100 text-red-800" : "bg-blue-100 text-blue-800"
                    }`}>
                      {v.status}
                    </span>
                    <span className="text-xs text-muted">• S:{v.maximumSpeedKph}kph</span>
                  </div>
                </div>
              </article>
            ))}
            {vehicles.length === 0 && (
              <p className="text-sm text-muted text-center py-6 col-span-2">No emergency vehicles registered.</p>
            )}
          </div>
        </div>

        {/* Right Column: Details & Edit Controls */}
        <div className="space-y-6">
          {selectedVehicle ? (
            <div className="bg-white rounded-xl border border-line shadow-sm p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div>
                  <h3 className="font-bold text-ink text-lg">{selectedVehicle.callSign}</h3>
                  <p className="text-xs text-muted">{selectedVehicle.vehicleType.replace("_", " ")}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(selectedVehicle)}
                  className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition border border-red-200"
                >
                  <Trash2 className="h-4.5 w-4.5" />
                </button>
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted">Status:</span>
                  <span className="font-bold text-ink">{selectedVehicle.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Capacity:</span>
                  <span className="font-bold text-ink">{selectedVehicle.capacity} crew</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Max Speed:</span>
                  <span className="font-bold text-ink">{selectedVehicle.maximumSpeedKph} kph</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Home Station:</span>
                  <span className="font-bold text-ink">{selectedVehicle.homeStation || "Mobile base"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Coordinates:</span>
                  <span className="font-bold text-ink">
                    {selectedVehicle.latitude.toFixed(4)}, {selectedVehicle.longitude.toFixed(4)}
                  </span>
                </div>
                {selectedVehicle.assignedIncidentId && (
                  <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-3 flex items-start gap-2.5">
                    <ShieldAlert className="h-4.5 w-4.5 text-indigo-700 mt-0.5" />
                    <div>
                      <p className="text-xs font-bold text-indigo-900">Active Duty</p>
                      <p className="text-xs text-indigo-700">Assigned to Incident #{selectedVehicle.assignedIncidentId}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Status Update Actions */}
              <div className="border-t border-line pt-4 space-y-2">
                <p className="text-xs font-semibold text-muted uppercase">Update Status</p>
                <div className="flex flex-wrap gap-2">
                  {["AVAILABLE", "RESERVED", "OUT_OF_SERVICE"].map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleStatusUpdate(selectedVehicle.id, s, selectedVehicle.version)}
                      disabled={selectedVehicle.status === s}
                      className="rounded border border-line px-2.5 py-1.5 text-xs font-semibold hover:bg-slate-50 disabled:opacity-50"
                    >
                      {s.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>

              {/* Location Update */}
              <div className="border-t border-line pt-4 space-y-3">
                <div className="flex justify-between items-center">
                  <p className="text-xs font-semibold text-muted uppercase">Fleet Location Desk</p>
                  <button
                    type="button"
                    onClick={() => setUpdatingLocation(!updatingLocation)}
                    className="text-xs text-teal-600 font-bold hover:underline inline-flex items-center gap-1"
                  >
                    <Edit2 className="h-3.5 w-3.5" /> Edit GPS
                  </button>
                </div>

                {updatingLocation ? (
                  <form onSubmit={handleLocationUpdate} className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <label className="grid gap-0.5 text-xs font-semibold text-ink">
                        Latitude
                        <input
                          type="number"
                          step="0.0001"
                          required
                          value={upLat}
                          onChange={(e) => setUpLat(Number(e.target.value))}
                          className="rounded border border-line px-2 py-1.5 text-xs focus:outline-none"
                        />
                      </label>
                      <label className="grid gap-0.5 text-xs font-semibold text-ink">
                        Longitude
                        <input
                          type="number"
                          step="0.0001"
                          required
                          value={upLng}
                          onChange={(e) => setUpLng(Number(e.target.value))}
                          className="rounded border border-line px-2 py-1.5 text-xs focus:outline-none"
                        />
                      </label>
                    </div>
                    <button
                      type="submit"
                      className="w-full text-center rounded bg-teal-600 text-white py-1.5 text-xs font-bold transition hover:bg-teal-700"
                    >
                      Apply Coordinates
                    </button>
                  </form>
                ) : (
                  <p className="text-xs text-muted flex items-center gap-1.5">
                    <MapPin className="h-4 w-4 text-muted" /> GPS Coordinates match model telemetry.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-xl border border-dashed border-line p-6 text-center text-muted text-sm">
              Select an emergency vehicle from the list to manage status updates, telemetry overrides, or decommission.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
