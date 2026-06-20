"use client";

import { useEffect, useState } from "react";
import { incidentEventsUrl } from "@/lib/api";

export function useIncidentEvents(onEvent: () => void, enabled = true) {
  const [connectionStatus, setConnectionStatus] = useState(enabled ? "connecting" : "paused");

  useEffect(() => {
    if (!enabled) {
      setConnectionStatus("paused");
      return;
    }
    const source = new EventSource(incidentEventsUrl());
    source.onopen = () => setConnectionStatus("connected");
    source.onerror = () => setConnectionStatus("reconnecting");
    source.addEventListener("incident", () => onEvent());
    return () => source.close();
  }, [enabled, onEvent]);

  return connectionStatus;
}
