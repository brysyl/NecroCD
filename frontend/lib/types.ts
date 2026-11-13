export interface Grave {
  branch: string;
  last_commit: string;
  last_commit_date: string;
  staleness_days: number;
  status: "broken" | "restable";
  findings: number;
}

export interface TelemetryEvent {
  id: string;
  type: string;
  ts: string;
  payload: Record<string, unknown>;
}

export interface PoltergeistPayload {
  cause: string;
  original: string;
  latin: string;
  severity: string;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function isTelemetryEvent(v: unknown): v is TelemetryEvent {
  return (
    isRecord(v) &&
    typeof v.id === "string" &&
    typeof v.type === "string" &&
    typeof v.ts === "string" &&
    isRecord(v.payload)
  );
}

export function isGrave(v: unknown): v is Grave {
  return (
    isRecord(v) &&
    typeof v.branch === "string" &&
    typeof v.last_commit === "string" &&
    typeof v.last_commit_date === "string" &&
    typeof v.staleness_days === "number" &&
    (v.status === "broken" || v.status === "restable") &&
    typeof v.findings === "number"
  );
}

export function isGraveList(v: unknown): v is Grave[] {
  return Array.isArray(v) && v.every(isGrave);
}

export function isTelemetryEventList(v: unknown): v is TelemetryEvent[] {
  return Array.isArray(v) && v.every(isTelemetryEvent);
}

/** Backend emits type "poltergeist" with payload.cause "test failure" | "dependency error" | "syntax rot". */
export function isPoltergeistPayload(v: unknown): v is PoltergeistPayload {
  return (
    isRecord(v) &&
    typeof v.cause === "string" &&
    typeof v.original === "string" &&
    typeof v.latin === "string" &&
    typeof v.severity === "string"
  );
}

const TRIGGER_TYPE = /(test[._-]?(fail|failure|failed)|dependency[._-]?error|poltergeist)/i;
const TRIGGER_CAUSE = /(test failure|dependency error|syntax rot)/i;

/** True for events that should haunt the UI: test failures and dependency errors (and syntax rot). */
export function isHauntingEvent(e: TelemetryEvent): boolean {
  if (TRIGGER_TYPE.test(e.type)) return true;
  const cause = e.payload.cause;
  return typeof cause === "string" && TRIGGER_CAUSE.test(cause);
}

function str(v: unknown, fallback: string): string {
  return typeof v === "string" && v.length > 0 ? v : fallback;
}

/** Normalizes any haunting event to a full payload, tolerating partial shapes. */
export function toPoltergeistPayload(e: TelemetryEvent): PoltergeistPayload {
  if (isPoltergeistPayload(e.payload)) return e.payload;
  const original = str(e.payload.original ?? e.payload.trace ?? e.payload.error ?? e.payload.message, e.type);
  return {
    cause: str(e.payload.cause, e.type.replace(/[._-]/g, " ")),
    original,
    latin: str(e.payload.latin, `Error detectus: ${original}\nRequiescat in pace.`),
    severity: str(e.payload.severity, "high"),
  };
}
