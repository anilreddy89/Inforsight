import {
  array,
  date,
  duration,
  money,
  object,
  text,
  words,
  type Audit,
  type Evidence,
  type Run,
  type ScenarioCatalog,
  type Stage,
  type StageStatus,
  type VisitorSession,
} from "./api";
import { BUNDLE_SHA256, type LiveProbe, type StageId } from "./architecture-model";

/**
 * Live evidence for the architecture explorer. Everything here is read from data
 * the page already holds (the polled run, session, scenario catalog and a loaded
 * audit); the explorer issues no requests of its own. Missing evidence is shown
 * as missing, never inferred.
 */
export type Connection = "loading" | "connected" | "disconnected";
export type LiveContext = {
  run: Run | null;
  session: VisitorSession | null;
  catalog: ScenarioCatalog | null;
  catalogError: Error | null;
  audit: Audit | null;
  connection: Connection;
  origin: string;
};
export type LiveState =
  | "idle"
  | "waiting"
  | "processing"
  | "partial"
  | "recorded"
  | "abstained"
  | "failed"
  | "blocked";
export type Fact = [string, string];

export const stageOrder: StageId[] = [
  "submission",
  "publication",
  "ingestion",
  "snapshot",
  "score",
  "rules",
  "allocation",
  "case",
  "agent",
  "decision",
  "audit",
];
const done = (status?: StageStatus) => status === "completed" || status === "abstained";

export function stageOf(run: Run | null, id: string): Stage | undefined {
  return run?.stages.find((stage) => stage.stage === id);
}

export function terminal(run: Run | null): boolean {
  return ["COMPLETED", "EXPIRED", "FAILED"].includes(run?.status ?? "");
}

/** The stage the backend is working on, or the latest recorded one. */
export function currentStage(run: Run | null): StageId | undefined {
  if (!run) return undefined;
  const find = (match: (stage: Stage) => boolean) =>
    run.stages.find(match)?.stage as StageId | undefined;
  return (
    find((stage) => stage.status === "processing") ??
    find((stage) => stage.status === "failed" || stage.status === "blocked") ??
    (run.status === "AWAITING_REVIEW" ? "decision" : undefined) ??
    [...stageOrder].reverse().find((id) => done(stageOf(run, id)?.status)) ??
    "submission"
  );
}

/** Aggregate persisted stage status for a component that owns several stages. */
export function stageState(
  run: Run | null,
  stages: StageId[] | undefined,
): { state: LiveState; recorded: number; total: number } {
  if (!run || !stages?.length) return { state: "idle", recorded: 0, total: 0 };
  const statuses = stages.map((id) => stageOf(run, id)?.status ?? "waiting");
  const recorded = statuses.filter(done).length;
  const total = statuses.length;
  const state: LiveState = statuses.includes("processing")
    ? "processing"
    : statuses.includes("failed")
      ? "failed"
      : recorded === total
        ? statuses.includes("abstained")
          ? "abstained"
          : "recorded"
        : statuses.includes("blocked")
          ? "blocked"
          : recorded > 0
            ? "partial"
            : "waiting";
  return { state, recorded, total };
}

export function stateLabel(state: LiveState, recorded: number, total: number): string {
  if (state === "partial") return `${recorded} of ${total} recorded`;
  if (state === "idle") return "reference";
  return state;
}

export function recordedDuration(run: Run | null, stages: StageId[] = stageOrder): number | undefined {
  const values = stages.flatMap((id) => {
    const value = stageOf(run, id)?.duration_ms;
    return typeof value === "number" ? [value] : [];
  });
  return values.length ? values.reduce((sum, value) => sum + value, 0) : undefined;
}

export function stageCount(run: Run | null, status: StageStatus): number {
  return run?.stages.filter((stage) => stage.status === status).length ?? 0;
}

/** Lifecycle states the run has passed, derived only from recorded stages. */
export function passedStates(run: Run | null): Set<string> {
  const passed = new Set<string>();
  if (!run) return passed;
  if (done(stageOf(run, "submission")?.status)) passed.add("WAITING");
  if (done(stageOf(run, "ingestion")?.status)) passed.add("PROCESSING");
  if (done(stageOf(run, "agent")?.status)) passed.add("AWAITING_REVIEW");
  if (run.status === "COMPLETED") passed.add("COMPLETED");
  const caseState = text(object(run.artifacts.case).state, "");
  if (caseState) passed.add(`case:${caseState}`);
  if (done(stageOf(run, "case")?.status)) passed.add("case:AWAITING_REVIEW");
  return passed;
}

const short = (value: unknown, length = 12): string => {
  const value_ = typeof value === "string" ? value : "";
  if (!value_) return "Not recorded";
  return value_.length > length + 1 ? `${value_.slice(0, length)}…` : value_;
};
const percent = (value: unknown): string =>
  typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "Not recorded";
const evidence = (run: Run | null, id: StageId): Evidence => object(stageOf(run, id)?.evidence);
const artifact = (run: Run | null, name: string): Evidence => object(run?.artifacts[name]);
const count = (value: unknown): number => (Array.isArray(value) ? value.length : 0);
const has = (value: unknown) => value !== undefined && value !== null && value !== "";
const yesNo = (value: unknown) =>
  value === true ? "Yes" : value === false ? "No" : "Unknown — evidence unavailable";

function connectionLabel(context: LiveContext): string {
  if (!context.run) return "No run open";
  if (context.connection === "connected")
    return terminal(context.run) ? "Persisted record loaded" : "Reading every 1.5 s";
  return context.connection === "loading" ? "Connecting" : "Interrupted; retrying with backoff";
}

function auditView(context: LiveContext): Evidence {
  const loaded = context.audit;
  const recorded = evidence(context.run, "audit");
  return loaded
    ? { ...recorded, ...loaded, source: "Loaded from GET /runs/{id}/audit" }
    : has(recorded.head_hash)
      ? { ...recorded, source: "Recorded by the audit stage" }
      : {};
}

function scoreFacts(score: Evidence): Fact[] {
  if (!has(score.calibrated_probability)) return [];
  const driver = array(score.top_risk_drivers)[0];
  return [
    ["Calibrated probability", percent(score.calibrated_probability)],
    ["Risk tier", words(score.risk_tier_id ?? score.risk_tier)],
    ["Bundle", `${text(score.bundle_id)} · v${text(score.bundle_version)}`],
    ["Bundle SHA-256", short(score.bundle_digest, 16)],
    ["Matches pinned release", score.bundle_digest === BUNDLE_SHA256 ? "Yes" : "No"],
    ["Top risk driver", driver ? `${words(driver.feature_name)} (+${text(driver.attribution_log_odds)} log-odds)` : "None recorded"],
    ["authorized_to_act", text(score.authorized_to_act)],
  ];
}

/** Detailed live facts for the inspector; null when the probe has nothing to show. */
export function liveFacts(probe: LiveProbe | undefined, context: LiveContext): Fact[] | null {
  if (!probe) return null;
  const { run, session, catalog } = context;
  const facts = (() => {
    switch (probe) {
      case "reviewer": {
        const decision = artifact(run, "decision");
        if (has(decision.decision))
          return [
            ["Recorded decision", words(decision.decision)],
            ["Case version", text(decision.case_version)],
            ["Committed", date(text(decision.committed_at, ""))],
            ["authorized_to_act", text(decision.authorized_to_act)],
          ] as Fact[];
        if (run?.status === "AWAITING_REVIEW") return [["Review", "Open and waiting for your decision"]] as Fact[];
        return run ? ([["Review", "Not yet available"]] as Fact[]) : [];
      }
      case "browser":
        return run
          ? ([
              ["Correlation ID", run.correlation_id],
              ["Run status", words(run.status)],
              ["Polling", connectionLabel(context)],
              ["Last persisted update", date(run.updated_at)],
            ] as Fact[])
          : ([
              ["Run", "None open; this is the reference model"],
              ["Session", session ? (session.public_mode ? "Signed visitor session" : "Local session") : "Connecting"],
            ] as Fact[]);
      case "edge":
        return session?.public_mode
          ? ([
              ["Serving origin", context.origin],
              ["Session expires", date(session.expires_at ?? undefined)],
              ["Session cookie", "HttpOnly, so this page cannot read it"],
            ] as Fact[])
          : session
            ? ([
                ["Serving origin", context.origin],
                ["Exposure", "Loopback only"],
              ] as Fact[])
            : [];
      case "gateway":
        return [
          ["Demo API", catalog ? "Reachable" : context.catalogError ? `Unreachable: ${context.catalogError.message}` : "Checking"],
          ...(catalog
            ? ([
                ["Scenarios enabled", `${catalog.scenarios.filter((item) => item.enabled).length} of ${catalog.scenarios.length}`],
                ["External execution", catalog.external_execution_enabled ? "Enabled" : "Disabled"],
              ] as Fact[])
            : []),
        ] as Fact[];
      case "control":
        return run
          ? ([
              ["Case", `${text(run.case_id)} · version ${text(run.case_version, "0")}`],
              ["Stages recorded", `${run.stages.filter((stage) => done(stage.status)).length} of ${run.stages.length}`],
              ["Recorded service time", duration(recordedDuration(run))],
              ["Environment", text(session?.environment)],
            ] as Fact[])
          : session
            ? ([
                ["Environment", session.environment],
                ["Visitor session", session.public_mode ? `Tag ${session.session_tag}` : "Local, no cookie required"],
              ] as Fact[])
            : [];
      case "kafka": {
        const published = evidence(run, "publication");
        const received = evidence(run, "ingestion");
        if (!has(published.topic) && !has(received.topic)) return run ? ([["Delivery", "Not yet published"]] as Fact[]) : [];
        return [
          ["Topic", text(published.topic ?? received.topic)],
          ["Partition · offset", `${text(published.partition ?? received.partition)} · ${text(published.offset ?? received.offset)}`],
          ["Producer acks", text(published.acks, "Recovered from delivery")],
          ["Broker timestamp", date(text(published.broker_timestamp, "") || undefined)],
          ["Consumer group", text(received.consumer_group, "Not yet consumed")],
          ["Envelope SHA-256", short(published.envelope_sha256 ?? received.envelope_sha256, 16)],
          ...(has(published.recovery) ? ([["Recovery", words(published.recovery)]] as Fact[]) : []),
        ] as Fact[];
      }
      case "postgres": {
        if (!run) return [];
        const verification = auditView(context);
        return [
          ["Run row", run.correlation_id],
          ["Case", `${text(run.case_id)} · version ${text(run.case_version, "0")}`],
          ["Case state", text(artifact(run, "case").state, "Not persisted yet")],
          ["Journal head", short(verification.head_hash, 16)],
          ["Verified entries", text(verification.verified_entries, "Not verified yet")],
        ] as Fact[];
      }
      case "inference":
      case "score": {
        const score = artifact(run, "score");
        const result = scoreFacts(score);
        return result.length ? result : run ? ([["Score", "Not recorded yet"]] as Fact[]) : [];
      }
      case "runtime": {
        if (!run) return [];
        const projection = artifact(run, "projection");
        const agent = artifact(run, "agent");
        const producer = object(projection.producer ?? agent.producer);
        const valuation = object(artifact(run, "allocation").valuation);
        return [
          ["Worker", text(producer.worker_id)],
          ["Snapshot", short(artifact(run, "snapshot").snapshot_id, 16)],
          ["Excluded later events", has(projection.excluded_event_ids) ? String(count(projection.excluded_event_ids)) : "Not recorded"],
          ["Economics contract", text(valuation.economics_contract_version)],
          ["Agent outcome", has(agent.status) ? words(agent.status) : "Not recorded"],
        ] as Fact[];
      }
      case "session": {
        if (!session) return [];
        if (!session.public_mode) return [["Mode", "Local: the visitor filter is disabled"]] as Fact[];
        const limits = session.limits;
        return [
          ["Submissions", `${text(limits.submissions_per_hour)} per hour`],
          ["Polls", `${text(limits.polls_per_minute)} per minute`],
          ["Retries", `${text(limits.retries_per_hour)} per hour`],
          ["Concurrent runs", text(limits.concurrent_processing_runs)],
          ["Retained runs", text(limits.retained_runs)],
          ["Retention", `${text(limits.retention_hours)} h · abandoned review ${text(limits.abandoned_review_hours)} h`],
          ["Session expires", date(session.expires_at ?? undefined)],
        ] as Fact[];
      }
      case "contract": {
        if (!catalog) return [];
        const inputs = object(catalog.safe_inputs);
        return [
          ...Object.entries(inputs).map(([name, bounds]) => {
            const range = object(bounds);
            return [words(name), `${text(range.minimum)} – ${text(range.maximum)}`] as Fact;
          }),
          ["External execution", catalog.external_execution_enabled ? "Enabled" : "Disabled"],
        ] as Fact[];
      }
      case "authority": {
        if (!run) return catalog ? ([["External execution", catalog.external_execution_enabled ? "Enabled" : "Disabled"]] as Fact[]) : [];
        return ["score", "rules", "allocation", "case", "agent", "decision"]
          .filter((name) => has(run.artifacts[name]))
          .map((name) => [words(name), `authorized_to_act: ${text(artifact(run, name).authorized_to_act)}`] as Fact);
      }
      case "integrity":
      case "journal": {
        const verification = auditView(context);
        if (!has(verification.head_hash)) return run ? ([["Verification", "Not run for this case yet"]] as Fact[]) : [];
        return [
          ["Result", verification.valid === true ? "Valid" : `Did not pass${has(verification.failure_code) ? `: ${text(verification.failure_code)}` : ""}`],
          ["Verified entries", text(verification.verified_entries)],
          ["Head hash", short(verification.head_hash, 16)],
          ["Externally anchored", "No"],
          ["Source", text(verification.source)],
        ] as Fact[];
      }
      case "source": {
        const source = evidence(run, "submission");
        const history = object(source.history);
        if (!has(source.policy_id)) return [];
        return [
          ["Scenario", words(source.scenario_id)],
          ["Policy events", String(count(history.policy_events))],
          ["Payment events", String(count(history.payment_events))],
          ["Safety events", String(count(history.safety_events))],
          ["Observation cutoff", date(text(source.as_of, "") || undefined)],
          ["Submitted event", text(source.event_id)],
        ] as Fact[];
      }
      case "projection": {
        const projection = artifact(run, "projection");
        if (!has(projection.feature_stage)) return [];
        return [
          ["Visible source events", String(count(projection.source_event_ids))],
          ["Excluded events", String(count(projection.excluded_event_ids))],
          ["Feature stage", text(projection.feature_stage)],
          ["Preprocessing", text(projection.preprocessing_profile_id)],
        ] as Fact[];
      }
      case "snapshot": {
        const snapshot = artifact(run, "snapshot");
        if (!has(snapshot.snapshot_id)) return [];
        const safety = object(snapshot.safety);
        const unknown = Object.values(safety).filter((value) => value === null).length;
        return [
          ["snapshot_id", short(snapshot.snapshot_id, 20)],
          ["As of", date(text(snapshot.as_of, "") || undefined)],
          ["Policy status", words(snapshot.status)],
          ["Tenure", `${text(snapshot.tenure_days)} days`],
          ["Days past due", text(snapshot.days_past_due)],
          ["In grace period", yesNo(snapshot.in_grace_period)],
          ["Unknown safety facts", String(unknown)],
        ] as Fact[];
      }
      case "features": {
        const features = object(artifact(run, "projection").features);
        if (!Object.keys(features).length) return [];
        return [
          ["Features", String(Object.keys(features).length)],
          ...["tenure_days", "recent_delay_days", "recent_failed_payment_count", "rolling_on_time_rate", "billing_frequency"].map(
            (name) => [words(name), text(features[name])] as Fact,
          ),
        ] as Fact[];
      }
      case "rules": {
        const rules = artifact(run, "rules");
        const results = array(rules.results);
        if (!results.length) return [];
        return [
          ["Rules version", text(rules.rules_version)],
          ...results.map(
            (rule) =>
              [
                words(rule.action_type),
                rule.eligible === true ? "Eligible" : `Ineligible · ${array(rule.reasons).length ? (rule.reasons as unknown[]).map(words).join(", ") : "see evidence"}`,
              ] as Fact,
          ),
        ] as Fact[];
      }
      case "valuation": {
        const valuation = object(artifact(run, "allocation").valuation);
        const candidates = array(valuation.candidates);
        if (!candidates.length) return [];
        return [
          ["Contract", `${text(valuation.economics_contract_id)} v${text(valuation.economics_contract_version)}`],
          ...candidates.map((candidate) => [words(candidate.action_type), `${money(candidate.net_utility_micros)} net · ${candidate.eligible === true ? "eligible" : "ineligible"}`] as Fact),
        ] as Fact[];
      }
      case "allocation": {
        const allocation = artifact(run, "allocation");
        if (!has(allocation.selected_action)) return [];
        return [
          ["Selected action", words(allocation.selected_action)],
          ["Modeled net value", money(allocation.objective_micros)],
          ["Budget used", `${money(allocation.used_money_micros)} of ${money(allocation.budget_micros)}`],
          ["Personnel used", `${text(allocation.used_personnel_seconds)} of ${text(allocation.personnel_seconds)} s`],
          ["Allocator", text(allocation.allocator_version)],
        ] as Fact[];
      }
      case "case": {
        const record = artifact(run, "case");
        if (!has(record.case_id)) return [];
        return [
          ["Case", `${text(record.case_id)} · version ${text(record.case_version)}`],
          ["State", text(record.state)],
          ["Snapshot digest", short(record.snapshot_digest, 16)],
          ["Score digest", short(record.score_digest, 16)],
          ["Rules digest", short(record.rules_digest, 16)],
          ["Allocation digest", short(record.allocation_digest, 16)],
        ] as Fact[];
      }
      case "agent": {
        const agent = artifact(run, "agent");
        if (!has(agent.status)) return [];
        return [
          ["Outcome", words(agent.status)],
          ["Action", has(agent.action_id) ? words(agent.action_id) : "None"],
          ["Reason codes", count(agent.reason_codes) ? (agent.reason_codes as unknown[]).map(words).join(", ") : "None"],
          ["Citation", count(agent.procedure_citations) ? (agent.procedure_citations as unknown[]).map((item) => text(item)).join(", ") : "None"],
          ["Evidence sources cited", String(count(agent.evidence_source_ids))],
          ["Input digest", short(agent.input_digest, 16)],
        ] as Fact[];
      }
      case "decision": {
        const decision = artifact(run, "decision");
        if (!has(decision.decision)) return [];
        return [
          ["Decision", words(decision.decision)],
          ["Case version", text(decision.case_version)],
          ["Reviewer label", text(decision.reviewer_id)],
          ["Committed", date(text(decision.committed_at, "") || undefined)],
          ["authorized_to_act", text(decision.authorized_to_act)],
        ] as Fact[];
      }
      case "runStatus":
        return run ? ([["Current run status", run.status], ["Last persisted update", date(run.updated_at)]] as Fact[]) : [];
      case "stageStatus":
        return run
          ? (["waiting", "processing", "completed", "abstained", "failed", "blocked"] as StageStatus[]).map(
              (status) => [status, String(stageCount(run, status))] as Fact,
            )
          : [];
      case "caseState": {
        const record = artifact(run, "case");
        return has(record.state)
          ? ([["Case state", text(record.state)], ["Case version", text(record.case_version)]] as Fact[])
          : [];
      }
      case "t_run":
        return run
          ? ([
              ["correlation_id", run.correlation_id],
              ["event_id", text(run.event_id)],
              ["status", run.status],
              ["created_at", date(run.created_at)],
              ["updated_at", date(run.updated_at)],
            ] as Fact[])
          : [];
      case "t_outbox": {
        const published = evidence(run, "publication");
        return run
          ? ([
              ["event_id", text(run.event_id)],
              ["published", has(published.acknowledged_at ?? published.confirmed_by_delivery_at) ? date(text(published.acknowledged_at ?? published.confirmed_by_delivery_at)) : "Not yet"],
              ["envelope SHA-256", short(published.envelope_sha256, 16)],
            ] as Fact[])
          : [];
      }
      case "t_inbox": {
        const received = evidence(run, "ingestion");
        return has(received.topic)
          ? ([
              ["topic", text(received.topic)],
              ["partition_id", text(received.partition)],
              ["record_offset", text(received.offset)],
              ["received_at", date(text(received.received_at, "") || undefined)],
            ] as Fact[])
          : [];
      }
      case "t_case": {
        const record = artifact(run, "case");
        return has(record.case_id)
          ? ([["case_id", text(record.case_id)], ["version", text(record.case_version)], ["state", text(record.state)]] as Fact[])
          : [];
      }
      case "t_decision": {
        const decision = artifact(run, "decision");
        return has(decision.idempotency_key)
          ? ([["idempotency_key", short(decision.idempotency_key, 16)], ["decision", text(decision.decision)]] as Fact[])
          : [];
      }
      case "t_journal": {
        const loaded = context.audit?.entries?.length;
        const verification = auditView(context);
        return loaded || has(verification.verified_entries)
          ? ([["rows", text(loaded ?? verification.verified_entries)], ["source", text(verification.source)]] as Fact[])
          : [];
      }
      case "t_checkpoint": {
        const verification = auditView(context);
        return has(verification.head_hash)
          ? ([["sequence", text(verification.verified_entries)], ["head_hash", short(verification.head_hash, 16)]] as Fact[])
          : [];
      }
      case "t_session":
        return session
          ? session.public_mode
            ? ([["Your session tag", session.session_tag], ["expires_at", date(session.expires_at ?? undefined)]] as Fact[])
            : ([["Rows", "None: local mode issues no sessions"]] as Fact[])
          : [];
    }
  })();
  return facts.length ? facts : null;
}

/** One short line drawn on the canvas; null keeps the component quiet. */
export function liveSummary(probe: LiveProbe | undefined, context: LiveContext): string | null {
  if (!probe) return null;
  const { run, session, catalog } = context;
  switch (probe) {
    case "reviewer": {
      const decision = artifact(run, "decision");
      return has(decision.decision) ? words(decision.decision) : run?.status === "AWAITING_REVIEW" ? "your turn" : null;
    }
    case "browser":
      return run ? (context.connection === "connected" ? (terminal(run) ? "record loaded" : "polling every 1.5 s") : "reconnecting") : null;
    case "edge":
      return session ? (session.public_mode ? "serving this page" : "loopback only") : null;
    case "gateway":
      return catalog ? "demo API reachable" : context.catalogError ? "API unreachable" : null;
    case "control":
      return run
        ? `${run.stages.filter((stage) => done(stage.status)).length}/${run.stages.length} stages recorded`
        : session
          ? session.public_mode ? "public mode" : "local mode"
          : null;
    case "kafka": {
      const published = evidence(run, "publication");
      return has(published.offset) ? `offset ${text(published.offset)} · partition ${text(published.partition)}` : null;
    }
    case "postgres":
      return run ? `case version ${text(run.case_version, "0")}` : null;
    case "inference":
    case "score": {
      const score = artifact(run, "score");
      return has(score.calibrated_probability) ? `p = ${percent(score.calibrated_probability)}` : null;
    }
    case "runtime": {
      const agent = artifact(run, "agent");
      const snapshot = artifact(run, "snapshot");
      return has(agent.status) ? `agent: ${words(agent.status)}` : has(snapshot.snapshot_id) ? `snapshot ${short(snapshot.snapshot_id, 8)}` : null;
    }
    case "session":
      return session?.public_mode ? `${text(session.limits.submissions_per_hour)} runs/h · ${text(session.limits.polls_per_minute)} polls/min` : session ? "off on loopback" : null;
    case "contract":
      return catalog ? "bounds served by the API" : null;
    case "authority":
      return run || catalog ? "authorized_to_act: false" : null;
    case "integrity":
    case "journal": {
      const verification = auditView(context);
      return has(verification.head_hash)
        ? `${verification.valid === true ? "valid" : "not valid"} · ${text(verification.verified_entries)} entries`
        : null;
    }
    case "source": {
      const history = object(evidence(run, "submission").history);
      const total = count(history.policy_events) + count(history.payment_events) + count(history.safety_events);
      return total ? `${total} source events` : null;
    }
    case "projection": {
      const projection = artifact(run, "projection");
      return has(projection.excluded_event_ids) ? `${count(projection.excluded_event_ids)} later event excluded` : null;
    }
    case "snapshot": {
      const snapshot = artifact(run, "snapshot");
      return has(snapshot.snapshot_id) ? `id ${short(snapshot.snapshot_id, 10)}` : null;
    }
    case "features": {
      const features = object(artifact(run, "projection").features);
      return Object.keys(features).length ? `${Object.keys(features).length} features · delay ${text(features.recent_delay_days)} d` : null;
    }
    case "rules": {
      const results = array(artifact(run, "rules").results);
      return results.length ? `${results.filter((rule) => rule.eligible === true).length} of ${results.length} eligible` : null;
    }
    case "valuation": {
      const candidates = array(object(artifact(run, "allocation").valuation).candidates);
      return candidates.length ? `${candidates.length} candidates valued` : null;
    }
    case "allocation": {
      const allocation = artifact(run, "allocation");
      return has(allocation.selected_action) ? `selected: ${words(allocation.selected_action)}` : null;
    }
    case "case": {
      const record = artifact(run, "case");
      return has(record.state) ? `${words(record.state)} · v${text(record.case_version)}` : null;
    }
    case "agent": {
      const agent = artifact(run, "agent");
      return has(agent.status) ? words(agent.status) : null;
    }
    case "decision": {
      const decision = artifact(run, "decision");
      return has(decision.decision) ? words(decision.decision) : null;
    }
    case "t_run":
      return run ? words(run.status) : null;
    case "t_inbox": {
      const received = evidence(run, "ingestion");
      return has(received.offset) ? `offset ${text(received.offset)}` : null;
    }
    case "t_case": {
      const record = artifact(run, "case");
      return has(record.case_id) ? `version ${text(record.case_version)}` : null;
    }
    case "t_journal": {
      const verification = auditView(context);
      return has(verification.verified_entries) ? `${text(verification.verified_entries)} rows verified` : null;
    }
    default:
      return null;
  }
}
