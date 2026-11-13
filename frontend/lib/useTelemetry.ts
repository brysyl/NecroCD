"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  isGraveList,
  isHauntingEvent,
  isTelemetryEvent,
  isTelemetryEventList,
  type Grave,
  type TelemetryEvent,
} from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS = API.replace(/^http/, "ws") + "/ws/telemetry";
const MOCK_INTERVAL_MS = 4000;

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

let seq = 0;
function mockEvent(type: string, payload: Record<string, unknown>): TelemetryEvent {
  seq += 1;
  return { id: `mock-${Date.now()}-${seq}`, type, ts: new Date().toISOString(), payload };
}

function mockPoltergeist(cause: string): TelemetryEvent {
  return mockEvent("poltergeist", { cause, original: MOCK_TRACE, latin: MOCK_LATIN, severity: "high" });
}

/** Cycles through realistic backend event shapes; a haunting every 5th tick. */
function nextMockEvent(tick: number): TelemetryEvent {
  const g = MOCK_GRAVES[tick % MOCK_GRAVES.length];
  switch (tick % 5) {
    case 0:
      return mockEvent("grave.discovered", { branch: g.branch, status: g.status, staleness_days: g.staleness_days });
    case 1:
      return mockEvent("exorcism.started", { target: `${g.branch}/app.py` });
    case 2:
      return mockEvent("exorcism.step", { attempt: 1, stage: "test" });
    case 3:
      return mockPoltergeist(tick % 10 === 3 ? "test failure" : "dependency error");
    default:
      return mockEvent("exorcism.completed", { target: `${g.branch}/app.py`, ok: false, attempts: 1, findings: g.findings });
  }
}

export interface Telemetry {
  graves: Grave[];
  events: TelemetryEvent[];
  eventCount: number;
  poltergeist: TelemetryEvent | null;
  connected: boolean;
  mock: boolean;
  simulate: () => void;
  dismiss: () => void;
}

export function useTelemetry(): Telemetry {
  const [graves, setGraves] = useState<Grave[]>(MOCK_GRAVES);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [eventCount, setEventCount] = useState(0);
  const [poltergeist, setPoltergeist] = useState<TelemetryEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const [mockGraves, setMockGraves] = useState(true);
  const retry = useRef(0);

  const handle = useCallback((e: TelemetryEvent) => {
    setEvents((prev) => [e, ...prev].slice(0, 100));
    setEventCount((n) => n + 1);
    if (isHauntingEvent(e)) setPoltergeist(e);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/graves`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: unknown) => {
        if (!cancelled && isGraveList(data) && data.length > 0) {
          setGraves(data);
          setMockGraves(false);
        }
      })
      .catch(() => {
        /* keep mock graves */
      });
    fetch(`${API}/api/telemetry`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: unknown) => {
        if (!cancelled && isTelemetryEventList(data)) {
          setEvents((prev) => (prev.length ? prev : [...data].reverse().slice(0, 100)));
        }
      })
      .catch(() => {
        /* backend offline */
      });

    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const open = () => {
      if (cancelled) return;
      ws = new WebSocket(WS);
      ws.onopen = () => {
        retry.current = 0;
        setConnected(true);
        setEvents((prev) => prev.filter((e) => !e.id.startsWith("mock-")));
      };
      ws.onmessage = (m: MessageEvent<unknown>) => {
        if (typeof m.data !== "string") return;
        try {
          const parsed: unknown = JSON.parse(m.data);
          if (isTelemetryEvent(parsed)) handle(parsed);
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

  // Mock telemetry keeps the UI alive while the websocket is unreachable; stops once connected.
  useEffect(() => {
    if (connected) return;
    let tick = 0;
    const id = setInterval(() => {
      handle(nextMockEvent(tick));
      tick += 1;
    }, MOCK_INTERVAL_MS);
    return () => clearInterval(id);
  }, [connected, handle]);

  const simulate = useCallback(() => handle(mockPoltergeist("test failure")), [handle]);
  const dismiss = useCallback(() => setPoltergeist(null), []);

  return { graves, events, eventCount, poltergeist, connected, mock: mockGraves || !connected, simulate, dismiss };
}
