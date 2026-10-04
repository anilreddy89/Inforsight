export type Evidence = Record<string, unknown>;
export type StageStatus =
  | "waiting"
  | "processing"
  | "completed"
  | "abstained"
  | "blocked"
  | "failed";
export type Stage = {
  stage: string;
  status: StageStatus;
  producer?: string;
  attempt?: number;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  input_refs?: unknown;
  output_refs?: unknown;
  evidence?: Evidence;
  error?: unknown;
};
export type Run = {
  correlation_id: string;
  event_id?: string;
  scenario_id: string;
  status: string;
  case_id?: string;
  case_version?: number;
  created_at: string;
  updated_at: string;
  stages: Stage[];
  artifacts: Record<string, Evidence | undefined>;
  audit?: Audit;
};
export type Scenario = {
  scenario_id: string;
  title: string;
  description: string;
  enabled: boolean;
  unavailable_reason?: string;
  inputs?: unknown;
  defaults?: Evidence;
  safe_overrides?: Evidence;
};
export type Audit = {
  valid: boolean;
  verified_entries?: number;
  head_hash?: string;
  scope?: string;
  entries?: Evidence[];
  failure_code?: string;
};
export type ScenarioCatalog = {
  scenarios: Scenario[];
  environment?: string;
  external_execution_enabled?: boolean;
  safe_inputs?: Evidence;
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/demo${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await response.text();
  let data: unknown;
  try {
    data = body ? JSON.parse(body) : {};
  } catch {
    throw new Error(
      `The service returned an unreadable response (${response.status}).`,
    );
  }
  if (!response.ok) {
    const value = data as Evidence;
    throw new Error(
      String(
        value.message ??
          value.detail ??
          value.error ??
          `Request failed (${response.status}).`,
      ),
    );
  }
  return data as T;
}

export function text(value: unknown, fallback = "Not available"): string {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
export function object(value: unknown): Evidence {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Evidence)
    : {};
}
export function array(value: unknown): Evidence[] {
  return Array.isArray(value) ? value.map(object) : [];
}
export function words(value: unknown): string {
  return text(value).replaceAll("_", " ").replaceAll("-", " ").toLowerCase();
}
export function date(value?: string): string {
  if (!value) return "Not recorded";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf())
    ? value
    : parsed.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "medium",
      });
}
export function duration(value?: number): string {
  if (value === undefined || value === null) return "—";
  return value < 1000
    ? `${Math.round(value)} ms`
    : `${(value / 1000).toFixed(2)} s`;
}
export function money(value: unknown): string {
  return typeof value === "number"
    ? (value / 1_000_000).toLocaleString("en-US", {
        style: "currency",
        currency: "USD",
      })
    : "Not available";
}
