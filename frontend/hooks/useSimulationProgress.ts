"use client";

import { useCallback, useRef, useState } from "react";
import { SIMULATION_WS_URL } from "@/lib/api";

export function useSimulationProgress() {
  const socketRef = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<string[]>([]);
  const [status, setStatus] = useState("idle");

  const startProgress = useCallback(() => {
    socketRef.current?.close();
    const socket = new WebSocket(SIMULATION_WS_URL);
    socketRef.current = socket;
    setEvents([]);
    setStatus("connecting");
    socket.onopen = () => {
      setStatus("connected");
      socket.send("start");
    };
    socket.onmessage = (message) => {
      const data = JSON.parse(message.data) as { status: string };
      setEvents((current) => [...current, data.status]);
      if (data.status === "COMPLETED" || data.status === "FAILED") {
        setStatus(data.status.toLowerCase());
        socket.close();
      }
    };
    socket.onerror = () => setStatus("failed");
  }, []);

  return { events, status, startProgress };
}
