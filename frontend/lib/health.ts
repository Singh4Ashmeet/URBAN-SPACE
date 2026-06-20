export type HealthState =
  | { state: "loading"; service?: undefined; message?: undefined }
  | { state: "up"; service: string; message: string }
  | { state: "degraded"; service?: string; message: string }
  | { state: "down"; service?: string; message: string };

type HealthResponse = {
  service?: string;
  status?: string;
};

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/api\/v1\/?$/, "");

export async function fetchServiceHealth(path: string): Promise<HealthState> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
    if (!response.ok) {
      return { state: "down", message: `HTTP ${response.status}` };
    }

    const data = (await response.json()) as HealthResponse;
    if (data.status === "UP" && data.service) {
      return { state: "up", service: data.service, message: "Healthy" };
    }

    return {
      state: "degraded",
      service: data.service,
      message: data.status ? `Unexpected status: ${data.status}` : "Missing health status"
    };
  } catch (error) {
    return {
      state: "down",
      message: error instanceof Error ? error.message : "Request failed"
    };
  }
}
