"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Grave, TelemetryEvent } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS = API.replace(/^http/, "ws") + "/ws/telemetry";

export const MOCK_GRAVES: Grave[] = [
  { branch: "feature/urllib2-port", last_commit: "a1b2c3d4e5", last_commit_date: "2022-03-01", staleness_days: 900, status: "broken", findings: 7 },
  { branch: "fix/queue-module", last_commit: "b2c3d4e5f6", last_commit_date: "2023-01-12", staleness_days: 620, status: "restable", findings: 2 },
  { branch: "pr/142-old-auth", last_commit: "c3d4e5f6a7", last_commit_date: "2021-11-20", staleness_days: 1100, status: "broken", findings: 12 },
  { branch: "chore/deps-bump", last_commit: "d4e5f6a7b8", last_commit_date: "2024-02-02", staleness_days: 200, status: "restable", findings: 1 },
  { branch: "pr/87-legacy-cache", last_commit: "e5f6a7b8c9", last_commit_date: "2023-06-30", staleness_days: 450, status: "restable", findings: 3 },
  { branch: "experiment/grpc", last_commit: "f6a7b8c9d0", last_commit_date: "2022-09-09", staleness_days: 760, status: "broken", findings: 5 },
];

const MOCK_TRACE = "Traceback (most recent call last):\n  File \"app.py\", line 3\nModuleNotFoundError: No module named 'urllib2'";
const MOCK_LATIN =
  "Vestigium retrorsum (ultima vocatio):\n  Fasciculus \"app.py\", linea 3\nErrorModuliNonInventi: Modulus 'urllib2' non est inventus.\nRequiescat in pace.";

function mockPoltergeist(): TelemetryEvent {
  return {
    id: `mock-${Date.now()}`,
    type: "poltergeist",
    ts: new Date().toISOString(),
    payload: { cause: "test failure", original: MOCK_TRACE, latin: MOCK_LATIN, severity: "high" },
  };
}

export function useTelemetry() {
  const [graves, setGraves] = useState<Grave[]>(MOCK_GRAVES);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [poltergeist, setPoltergeist] = useState<TelemetryEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const [mock, setMock] = useState(true);
  const retry = useRef(0);

  const handle = useCallback((e: TelemetryEvent) => {
    setEvents((prev) => [e, ...prev].slice(0, 100));
    if (e.type === "poltergeist") setPoltergeist(e);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/graves`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: Grave[]) => {
        if (!cancelled && Array.isArray(data) && data.length) {
          setGraves(data);
          setMock(false);
        }
      })
      .catch(() => {
        /* keep mock data */
      });

    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const open = () => {
      if (cancelled) return;
      ws = new WebSocket(WS);
      ws.onopen = () => {
        retry.current = 0;
        setConnected(true);
      };
      ws.onmessage = (m) => {
        try {
          handle(JSON.parse(m.data) as TelemetryEvent);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (cancelled) return;
        const delay = Math.min(30000, 1000 * 2 ** retry.current++);
        timer = setTimeout(open, delay);
      };
      ws.onerror = () => ws?.close();
    };
    open();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, [handle]);

  const simulate = useCallback(() => handle(mockPoltergeist()), [handle]);
  const dismiss = useCallback(() => setPoltergeist(null), []);

  return { graves, events, poltergeist, connected, mock, simulate, dismiss };
}
