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
