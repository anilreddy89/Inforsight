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

export type VisitorSession = {
  public_mode: boolean;
  session_tag: string;
  csrf_token: string | null;
  expires_at: string | null;
  environment: "local" | "public-preview";
  limits: Record<string, number>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly retryAfterSeconds = 0,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function asError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value));
}
export function requestTitle(error: Error): string {
  if (!(error instanceof ApiError)) return "The connection needs attention";
  if (error.status === 401) return "Your visitor session is unavailable";
  if (error.status === 403) return "Your visitor session needs to be refreshed";
  if (error.status === 404) return "This run is unavailable in this browser";
  if (error.status === 410) return "This run’s retention period has ended";
  if (error.status === 429) return "Please give the demo a moment";
  if (error.code === "DEMO_CAPACITY") return "The preview is at capacity";
  if (error.status >= 500) return "Demo services are temporarily unavailable";
  return "The request could not be completed";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/demo${path}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await response.text();
  let data: unknown;
  try {
    data = body ? JSON.parse(body) : {};
  } catch {
    throw new ApiError(
      response.status >= 500
        ? "The preview gateway cannot reach its services. Please try again shortly."
        : `The service returned an unreadable response (${response.status}).`,
      response.status,
      "UNREADABLE_RESPONSE",
    );
  }
  if (!response.ok) {
    const value = data as Evidence;
    const retryHeader = response.headers.get("Retry-After");
    const retrySeconds = retryHeader
      ? (/^\d+$/.test(retryHeader) ? Number(retryHeader) : Math.max(0, (Date.parse(retryHeader) - Date.now()) / 1000))
      : Number(value.retry_after_seconds ?? 0);
    let message = String(value.message ?? value.detail ?? value.error ?? `Request failed (${response.status}).`);
    if (response.status === 401 || response.status === 403)
      message += " Reload the page to establish your visitor session. Clearing cookies removes access to earlier runs.";
    if (response.status === 404)
      message = "A correlation ID does not grant access. Use the browser and website address that created this run, with its original visitor cookie.";
    if (response.status === 410)
      message = "The backend has removed this temporary run under its retention policy. You can start a new fictional case.";
    if (retrySeconds > 0)
      message += ` Try again after ${new Date(Date.now() + retrySeconds * 1000).toLocaleTimeString()}. Your recorded stage evidence is unchanged.`;
    throw new ApiError(message, response.status, String(value.code ?? "REQUEST_FAILED"), Number.isFinite(retrySeconds) ? retrySeconds : 0);
  }
  return data as T;
}

let visitorSession: Promise<VisitorSession> | undefined;
export function getSession(): Promise<VisitorSession> {
  // Cookie authentication stays HttpOnly; only the CSRF proof is held in memory.
  visitorSession ??= request<VisitorSession>("/session").catch((error) => {
    visitorSession = undefined;
    throw error;
  });
  return visitorSession;
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const session = await getSession();
  const mutating = init?.method && !["GET", "HEAD"].includes(init.method.toUpperCase());
  return request<T>(path, {
    ...init,
    headers: {
      ...init?.headers,
      ...(mutating && session.csrf_token ? { "X-Demo-CSRF": session.csrf_token } : {}),
    },
  });
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
