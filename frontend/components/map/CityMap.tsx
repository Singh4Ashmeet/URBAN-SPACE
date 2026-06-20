"use client";

import maplibregl, { type GeoJSONSource, type Map, type Marker, type StyleSpecification } from "maplibre-gl";
import { useEffect, useRef, useState, type MouseEvent } from "react";
import type { Incident } from "@/types/incidents";
import type { EmergencyVehicle } from "@/types/allocation";

type CityMapProps = {
  incidents: Incident[];
  selectedIncident?: Incident | null;
  onSelectIncident: (incident: Incident) => void;
  is3d: boolean;
  scenarioPoint: { latitude: number; longitude: number } | null;
  onPlaceScenario: (point: { latitude: number; longitude: number }) => void;
  vehicles?: EmergencyVehicle[];
  compact?: boolean;
};

const MAP_CENTER: [number, number] = [77.209, 28.614];

const cityMapStyle: StyleSpecification = {
  version: 8,
  sources: {
    "carto-voyager": {
      type: "raster",
      tiles: ["/api/map-tiles/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
    }
  },
  layers: [
    {
      id: "carto-voyager",
      type: "raster",
      source: "carto-voyager",
      minzoom: 0,
      maxzoom: 20
    }
  ]
};

const severityColor = (severity: number) => {
  if (severity >= 5) return "#b42318";
  if (severity >= 4) return "#dc6803";
  if (severity >= 3) return "#cc7a00";
  return "#087669";
};

export function CityMap({ incidents, selectedIncident, onSelectIncident, is3d, scenarioPoint, onPlaceScenario, vehicles = [], compact = false }: CityMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const scenarioMarkerRef = useRef<Marker | null>(null);
  const vehicleMarkersRef = useRef<Marker[]>([]);
  const animationFrameRef = useRef<number | null>(null);
  const onPlaceScenarioRef = useRef(onPlaceScenario);
  const onSelectIncidentRef = useRef(onSelectIncident);
  const [useFallbackMap, setUseFallbackMap] = useState(false);

  useEffect(() => {
    onPlaceScenarioRef.current = onPlaceScenario;
  }, [onPlaceScenario]);

  useEffect(() => {
    onSelectIncidentRef.current = onSelectIncident;
  }, [onSelectIncident]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current || useFallbackMap) return;

    let map: Map;
    try {
      map = new maplibregl.Map({
        attributionControl: false,
        center: MAP_CENTER,
        container: containerRef.current,
        cooperativeGestures: true,
        pitch: is3d ? 48 : 0,
        style: cityMapStyle,
        zoom: 13.25
      });
    } catch {
      window.setTimeout(() => setUseFallbackMap(true), 0);
      return;
    }
    mapRef.current = map;
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");
    map.on("click", (event) => onPlaceScenarioRef.current({ latitude: event.lngLat.lat, longitude: event.lngLat.lng }));

    return () => {
      if (animationFrameRef.current) window.cancelAnimationFrame(animationFrameRef.current);
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      vehicleMarkersRef.current.forEach((marker) => marker.remove());
      vehicleMarkersRef.current = [];
      scenarioMarkerRef.current?.remove();
      scenarioMarkerRef.current = null;
      map.remove();
      mapRef.current = null;
    };
  }, [is3d, useFallbackMap]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.easeTo({ bearing: is3d ? -18 : 0, duration: 500, pitch: is3d ? 48 : 0 });
  }, [is3d]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = incidents.map((incident) => {
      const element = document.createElement("button");
      element.type = "button";
      element.className = "map-incident-marker";
      element.textContent = String(incident.severity);
      element.setAttribute("aria-label", `Select ${incident.title}`);
      element.style.backgroundColor = severityColor(incident.severity);
      element.addEventListener("click", (event) => {
        event.stopPropagation();
        onSelectIncidentRef.current(incident);
      });
      return new maplibregl.Marker({ element }).setLngLat([incident.longitude, incident.latitude]).addTo(map);
    });

    if (incidents.length > 0) {
      const firstIncident = incidents[0];
      const bounds = incidents.reduce(
        (nextBounds, incident) => nextBounds.extend([incident.longitude, incident.latitude]),
        new maplibregl.LngLatBounds([firstIncident.longitude, firstIncident.latitude], [firstIncident.longitude, firstIncident.latitude])
      );
      map.fitBounds(bounds, { duration: 600, maxZoom: 14.2, padding: 86 });
    }
  }, [incidents]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !scenarioPoint) return;

    if (!scenarioMarkerRef.current) {
      const element = document.createElement("span");
      element.className = "map-scenario-marker";
      scenarioMarkerRef.current = new maplibregl.Marker({ element });
    }
    scenarioMarkerRef.current.setLngLat([scenarioPoint.longitude, scenarioPoint.latitude]).addTo(map);
  }, [scenarioPoint]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !scenarioPoint) return;

    const routeVehicles = vehicles
      .filter((vehicle) => Number.isFinite(vehicle.latitude) && Number.isFinite(vehicle.longitude))
      .slice(0, 4);

    if (animationFrameRef.current) window.cancelAnimationFrame(animationFrameRef.current);
    vehicleMarkersRef.current.forEach((marker) => marker.remove());
    vehicleMarkersRef.current = [];

    const routes = routeVehicles.map((vehicle) => ({
      type: "Feature" as const,
      properties: { id: vehicle.id },
      geometry: {
        type: "LineString" as const,
        coordinates: [
          [vehicle.longitude, vehicle.latitude],
          [scenarioPoint.longitude, scenarioPoint.latitude]
        ]
      }
    }));

    const updateRoutes = () => {
      const data = { type: "FeatureCollection" as const, features: routes };
      if (!map.getSource("vehicle-routes")) {
        map.addSource("vehicle-routes", { type: "geojson", data });
        map.addLayer({
          id: "vehicle-routes-line",
          type: "line",
          source: "vehicle-routes",
          paint: {
            "line-color": "#087669",
            "line-dasharray": [2, 2],
            "line-opacity": 0.82,
            "line-width": 3
          }
        });
      } else {
        const source = map.getSource("vehicle-routes") as GeoJSONSource | undefined;
        source?.setData(data);
      }
    };

    if (map.isStyleLoaded()) updateRoutes();
    else map.once("load", updateRoutes);

    if (routeVehicles.length === 0) return;

    vehicleMarkersRef.current = routeVehicles.map((vehicle) => {
      const element = document.createElement("span");
      element.className = "map-vehicle-marker";
      element.setAttribute("aria-label", `${vehicle.callSign} moving to scenario point`);
      element.title = `${vehicle.callSign} - ${vehicle.vehicleType.replaceAll("_", " ")}`;
      return new maplibregl.Marker({ element }).setLngLat([vehicle.longitude, vehicle.latitude]).addTo(map);
    });

    const startedAt = performance.now();
    const animateVehicles = (time: number) => {
      const progress = ((time - startedAt) % 4200) / 4200;
      const eased = progress < 0.5 ? progress * 2 : 2 - progress * 2;
      routeVehicles.forEach((vehicle, index) => {
        const longitude = vehicle.longitude + (scenarioPoint.longitude - vehicle.longitude) * eased;
        const latitude = vehicle.latitude + (scenarioPoint.latitude - vehicle.latitude) * eased;
        vehicleMarkersRef.current[index]?.setLngLat([longitude, latitude]);
      });
      animationFrameRef.current = window.requestAnimationFrame(animateVehicles);
    };
    animationFrameRef.current = window.requestAnimationFrame(animateVehicles);

    return () => {
      if (animationFrameRef.current) window.cancelAnimationFrame(animationFrameRef.current);
      vehicleMarkersRef.current.forEach((marker) => marker.remove());
      vehicleMarkersRef.current = [];
    };
  }, [scenarioPoint, vehicles]);

  return (
    <section
      className={`relative overflow-hidden rounded-lg border border-line bg-white ${compact ? "min-h-[320px]" : "min-h-[520px]"} ${useFallbackMap && is3d ? "city-map-tilted" : ""}`}
      aria-label="Interactive incident map"
    >
      <div ref={containerRef} className="absolute inset-0" aria-hidden={useFallbackMap ? "true" : undefined} />
      {useFallbackMap ? (
        <FallbackMap incidents={incidents} scenarioPoint={scenarioPoint} onPlaceScenario={onPlaceScenario} onSelectIncident={onSelectIncident} vehicles={vehicles} />
      ) : null}
      {selectedIncident ? (
        <aside className="absolute bottom-4 left-4 right-4 rounded-lg border border-line bg-white p-4 shadow-soft md:left-auto md:w-96">
          <p className="text-xs font-bold uppercase text-muted">{selectedIncident.incidentType.replaceAll("_", " ")}</p>
          <h3 className="mt-1 text-lg font-semibold text-ink">{selectedIncident.title}</h3>
          <p className="mt-2 text-sm text-muted">Severity {selectedIncident.severity} - {selectedIncident.status.replaceAll("_", " ")}</p>
        </aside>
      ) : null}
    </section>
  );
}

type FallbackMapProps = Pick<CityMapProps, "incidents" | "scenarioPoint" | "onPlaceScenario" | "onSelectIncident" | "vehicles">;

function FallbackMap({ incidents, scenarioPoint, onPlaceScenario, onSelectIncident, vehicles = [] }: FallbackMapProps) {
  function handlePlaceScenario(event: MouseEvent<HTMLElement>) {
    if (event.target !== event.currentTarget) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    onPlaceScenario({
      longitude: MAP_CENTER[0] + (x * 100 - 48) / 1800,
      latitude: MAP_CENTER[1] - (y * 100 - 50) / 1800
    });
  }

  return (
    <div className="absolute inset-0" onClick={handlePlaceScenario}>
      <div className="absolute inset-0 city-map-surface" aria-hidden="true">
        <span className="city-road city-road-a" />
        <span className="city-road city-road-b" />
        <span className="city-road city-road-c" />
        <span className="city-zone city-zone-a" />
        <span className="city-zone city-zone-b" />
        <span className="city-zone city-zone-c" />
      </div>
      <div className="pointer-events-none absolute inset-0">
        {scenarioPoint ? vehicles.slice(0, 4).map((vehicle) => {
          const vehicleLeft = clamp(48 + (vehicle.longitude - MAP_CENTER[0]) * 1800, 4, 96);
          const vehicleTop = clamp(50 - (vehicle.latitude - MAP_CENTER[1]) * 1800, 4, 96);
          const targetLeft = clamp(48 + (scenarioPoint.longitude - MAP_CENTER[0]) * 1800, 4, 96);
          const targetTop = clamp(50 - (scenarioPoint.latitude - MAP_CENTER[1]) * 1800, 4, 96);
          return (
            <span
              key={vehicle.id}
              className="map-fallback-route"
              style={{
                left: `${vehicleLeft}%`,
                top: `${vehicleTop}%`,
                width: `${Math.hypot(targetLeft - vehicleLeft, targetTop - vehicleTop)}%`,
                transform: `rotate(${Math.atan2(targetTop - vehicleTop, targetLeft - vehicleLeft)}rad)`
              }}
              aria-hidden="true"
            >
              <span className="map-vehicle-marker" />
            </span>
          );
        }) : null}
        {incidents.map((incident) => (
          <button
            key={incident.id}
            type="button"
            aria-label={`Select ${incident.title}`}
            onClick={() => onSelectIncident(incident)}
            className="map-incident-marker pointer-events-auto absolute"
            style={{
              backgroundColor: severityColor(incident.severity),
              left: `${clamp(48 + (incident.longitude - MAP_CENTER[0]) * 1800, 4, 96)}%`,
              top: `${clamp(50 - (incident.latitude - MAP_CENTER[1]) * 1800, 4, 96)}%`
            }}
          >
            {incident.severity}
          </button>
        ))}
        {scenarioPoint ? (
          <span
            className="map-scenario-marker absolute"
            style={{
              left: `${clamp(48 + (scenarioPoint.longitude - MAP_CENTER[0]) * 1800, 4, 96)}%`,
              top: `${clamp(50 - (scenarioPoint.latitude - MAP_CENTER[1]) * 1800, 4, 96)}%`
            }}
            aria-hidden="true"
          />
        ) : null}
      </div>
    </div>
  );
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}
