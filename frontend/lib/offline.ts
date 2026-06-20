import { openDB } from "idb";
import type { Incident } from "@/types/incidents";
import type { SimulationRequest, SimulationResponse } from "@/types/simulation";

const DB_NAME = "urbanshield-phase2";

async function db() {
  return openDB(DB_NAME, 1, {
    upgrade(database) {
      database.createObjectStore("incidents");
      database.createObjectStore("scenarios");
      database.createObjectStore("drafts", { keyPath: "scenario_name" });
    }
  });
}

export async function cacheIncidents(incidents: Incident[]) {
  const database = await db();
  await database.put("incidents", incidents, "latest");
}

export async function getCachedIncidents(): Promise<Incident[]> {
  const database = await db();
  return (await database.get("incidents", "latest")) ?? [];
}

export async function cacheScenario(result: SimulationResponse) {
  const database = await db();
  await database.put("scenarios", result, result.simulation_id);
}

export async function queueDraftScenario(request: SimulationRequest) {
  const database = await db();
  await database.put("drafts", { ...request, queuedAt: new Date().toISOString() });
}
