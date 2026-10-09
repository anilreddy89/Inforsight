import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  Circle,
  CircleDashed,
  Clock3,
  Code2,
  Copy,
  Database,
  FileCheck2,
  FileText,
  Fingerprint,
  GitBranch,
  History,
  Info,
  Layers3,
  LockKeyhole,
  Network,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  ShieldX,
  SlidersHorizontal,
  Sparkles,
  X,
  type LucideIcon,
} from "./icons";
import {
  api,
  ApiError,
  asError,
  getSession,
  requestTitle,
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
import TransactionFlow from "./TransactionFlow";
import RecentRuns from "./RecentRuns";
import ArchitectureTeaser from "./ArchitectureTeaser";
import ModelBand from "./ModelBand";
import { useRecentRuns } from "./recent-runs";
import type { LensId } from "./architecture-lenses";

// The architecture model is large; load it only when the view is opened.
const ArchitectureExplorer = lazy(() => import("./ArchitectureExplorer"));
const ModelTimeline = lazy(() => import("./ModelTimeline"));

type View = "journey" | "flow" | "dossier" | "review" | "audit" | "architecture" | "model";
/** Only the flow, architecture and model views are addressable; other views follow the run. */
function viewFromUrl(): View {
  const value = new URLSearchParams(window.location.search).get("view");
  return value === "flow" || value === "architecture" || value === "model" ? value : "journey";
}
function stored<T>(key: string): T | null {
  try {
    const value = sessionStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : null;
  } catch {
    return null;
  }
}
function remember(key: string, value: unknown) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* Private browser storage may be unavailable. The active request remains idempotent. */
  }
}
type PendingSubmission = {
  key: string;
  scenario_id: string;
  overrides: Evidence;
};

const stageInfo: Record<
  string,
  { title: string; description: string; icon: LucideIcon; component: string }
> = {
  submission: {
    title: "Event submitted",
    description: "A fictional policy event is accepted with a unique identity.",
    icon: ArrowUpRight,
    component: "Java control plane",
  },
  publication: {
    title: "Event published",
    description: "The event bus acknowledges the event for delivery.",
    icon: Network,
    component: "Kafka event bus",
  },
  ingestion: {
    title: "Event received",
    description:
      "The Java consumer records the event and checks for duplicates.",
    icon: ArrowDown,
    component: "Java control plane",
  },
  snapshot: {
    title: "Policy snapshot",
    description:
      "Only policy facts available at the observation time are included.",
    icon: Layers3,
    component: "Python evidence projection",
  },
  score: {
    title: "Modeled risk",
    description:
      "The released model scores the snapshot and explains its prediction.",
    icon: Activity,
    component: "Python inference",
  },
  rules: {
    title: "Eligibility rules",
    description:
      "Deterministic rules decide which recommendations are permitted.",
    icon: ShieldCheck,
    component: "Java control plane",
  },
  allocation: {
    title: "Portfolio allocation",
    description:
      "Eligible recommendations are evaluated against modeled value and capacity.",
    icon: GitBranch,
    component: "Java control plane",
  },
  case: {
    title: "Case persisted",
    description: "The case and its evidence become a durable record.",
    icon: Database,
    component: "PostgreSQL",
  },
  agent: {
    title: "Advisory draft",
    description:
      "The bounded agent cites trusted evidence or explicitly abstains.",
    icon: Sparkles,
    component: "Python agent workflow",
  },
  decision: {
    title: "Human decision",
    description:
      "A reviewer records a decision. The agent cannot authorize action.",
    icon: FileCheck2,
    component: "Java control plane",
  },
  audit: {
    title: "Audit verified",
    description: "The persisted record chain is checked for integrity.",
    icon: Fingerprint,
    component: "PostgreSQL / audit",
  },
};
const orderedStages = Object.keys(stageInfo);
const views: { id: View; label: string; icon: LucideIcon }[] = [
  { id: "journey", label: "Live journey", icon: GitBranch },
  { id: "flow", label: "Transaction flow", icon: Activity },
  { id: "dossier", label: "Case dossier", icon: FileText },
  { id: "review", label: "Human review", icon: FileCheck2 },
  { id: "audit", label: "Audit trail", icon: Fingerprint },
  { id: "architecture", label: "Architecture", icon: Network },
];
const scenarioCopy = [
  {
    id: "late-payment",
    title: "A payment falls behind",
    label: "The complete journey",
    description:
      "A fictional late payment prompts risk assessment, a bounded recommendation, and your review.",
    icon: Clock3,
  },
  {
    id: "missing-safety-evidence",
    title: "Safety evidence is missing",
    label: "A rule boundary",
    description:
      "See how unknown safety facts restrict eligible recommendations and remain visible in the case.",
    icon: ShieldX,
  },
  {
    id: "agent-abstention",
    title: "The agent must abstain",
    label: "An evidence boundary",
    description:
      "Follow a case where the bounded agent cannot support a draft and explains why it stops.",
    icon: Pause,
  },
];

function Badge({ status, children }: { status?: string; children: ReactNode }) {
  return (
    <span className={`badge ${status ? `badge-${status.toLowerCase()}` : ""}`}>
      {children}
    </span>
  );
}
function StatusIcon({ status }: { status: StageStatus }) {
  const Icon =
    status === "completed"
      ? Check
      : status === "abstained"
        ? Pause
        : status === "failed"
          ? X
          : status === "blocked"
            ? LockKeyhole
            : status === "processing"
              ? Activity
              : Circle;
  return (
    <span className={`status-icon status-${status}`}>
      <Icon size={16} aria-hidden="true" />
    </span>
  );
}
function Technical({
  value,
  label = "Inspect technical evidence",
}: {
  value: unknown;
  label?: string;
}) {
  return (
    <details className="technical">
      <summary>
        <Code2 size={15} />
        {label}
        <ChevronDown size={15} />
      </summary>
      <pre>{JSON.stringify(value, null, 2) ?? "No evidence recorded."}</pre>
    </details>
  );
}
function Empty({
  title,
  children,
  icon: Icon = CircleDashed,
}: {
  title: string;
  children: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="empty">
      <Icon size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function CopyValue({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="copy-value"
      aria-label={`Copy ${label}`}
      title={value}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
        } catch {
          setCopied(false);
        }
      }}
    >
      <code>{value}</code>
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  );
}
function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
function Panel({
  title,
  eyebrow,
  icon: Icon,
  children,
  className = "",
}: {
  title: string;
  eyebrow?: string;
  icon?: LucideIcon;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2>{title}</h2>
        </div>
        {Icon && <Icon size={21} className="muted" />}
      </div>
      {children}
    </section>
  );
}

export default function App() {
  const initialId =
    new URLSearchParams(window.location.search).get("run") ?? "";
  const pendingSubmission = useRef(
    stored<PendingSubmission>("inforsight.pending-submission"),
  );
  const [runId, setRunId] = useState(initialId);
  const [run, setRun] = useState<Run | null>(null);
  const [view, setView] = useState<View>(viewFromUrl);
  const [catalog, setCatalog] = useState<ScenarioCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<Error | null>(null);
  const [session, setSession] = useState<VisitorSession | null>(null);
  const [cookieNoticeDismissed, setCookieNoticeDismissed] = useState(
    () => stored<boolean>("inforsight.cookie-notice.v1") === true,
  );
  const cookieNoticeLink = useRef<HTMLButtonElement>(null);
  // The model timeline is a standalone page; Back returns to the view (and lens) that opened it.
  const [modelReturn, setModelReturn] = useState<{ view: View; lens?: LensId }>({ view: "journey" });
  const [modelFocus, setModelFocus] = useState<string>();
  const [architectureSeen, setArchitectureSeen] = useState(
    () => stored<boolean>("inforsight.architecture-seen.v1") === true,
  );
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState<
    "loading" | "connected" | "disconnected"
  >("loading");
  const [selected, setSelected] = useState(
    pendingSubmission.current?.scenario_id ?? "late-payment",
  );
  const [overrideText, setOverrideText] = useState(
    JSON.stringify(pendingSubmission.current?.overrides ?? {}, null, 2),
  );
  const [resume, setResume] = useState("");
  const [recentOpen, setRecentOpen] = useState(false);
  const recentRuns = useRecentRuns(run?.correlation_id === runId ? run : null, session);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [auditBusy, setAuditBusy] = useState(false);
  const submissionKey = useRef(pendingSubmission.current?.key ?? "");
  const requestSequence = useRef(0);

  useEffect(() => {
    if (runId && error instanceof ApiError && [404, 410].includes(error.status)) {
      recentRuns.markUnavailable(runId, error.status);
    }
  }, [runId, error, recentRuns.markUnavailable]);

  useEffect(() => {
    if (view !== "architecture" || architectureSeen) return;
    setArchitectureSeen(true);
    remember("inforsight.architecture-seen.v1", true);
  }, [view, architectureSeen]);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (view === "flow" || view === "architecture" || view === "model") url.searchParams.set("view", view);
    else url.searchParams.delete("view");
    window.history.replaceState({}, "", url);
  }, [view]);

  const loadCatalog = useCallback(async () => {
    try {
      const currentSession = await getSession();
      const previousTag = stored<string>("inforsight.visitor-tag");
      if (previousTag !== currentSession.session_tag) {
        // A new cookie must never claim to recover another visitor’s pending POST.
        pendingSubmission.current = null;
        submissionKey.current = "";
        remember("inforsight.pending-submission", null);
        remember("inforsight.visitor-tag", currentSession.session_tag);
      }
      setSession(currentSession);
      const response = await api<ScenarioCatalog>("/scenarios");
      setCatalog(response);
      setCatalogError(null);
    } catch (e) {
      setCatalogError(asError(e));
    }
  }, []);
  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);
  const refreshRun = useCallback(async (id: string) => {
    const sequence = ++requestSequence.current;
    try {
      const response = await api<Run>(`/runs/${encodeURIComponent(id)}`);
      if (sequence !== requestSequence.current) return;
      setRun((previous) =>
        previous?.correlation_id === response.correlation_id &&
        Date.parse(previous.updated_at) > Date.parse(response.updated_at)
          ? previous
          : response,
      );
      setConnection("connected");
      setError(null);
      if (response.audit) setAudit(response.audit);
      return { connected: true, delay: 1500, stop: ["COMPLETED", "EXPIRED"].includes(response.status) };
    } catch (e) {
      if (sequence === requestSequence.current) {
        setConnection("disconnected");
        setError(asError(e));
      }
      return {
        connected: false,
        delay: e instanceof ApiError ? Math.max(1500, e.retryAfterSeconds * 1000) : 1500,
        stop: e instanceof ApiError && [401, 403, 404, 410].includes(e.status),
      };
    }
  }, []);
  useEffect(() => {
    if (!runId) return;
    setConnection("loading");
    let active = true;
    let timer = 0;
    let failures = 0;
    // Schedule the next read only after this one finishes. Slow services cannot
    // starve successful responses; no elapsed timer changes workflow status.
    const poll = async () => {
      if (!active) return;
      let serverDelay = 0;
      if (document.visibilityState === "visible") {
        const result = await refreshRun(runId);
        if (result?.stop) return;
        failures = result?.connected ? 0 : Math.min(failures + 1, 3);
        serverDelay = result?.delay ?? 0;
      }
      if (active)
        timer = window.setTimeout(poll, Math.max(serverDelay, Math.min(1500 * 2 ** failures, 10000)));
    };
    void poll();
    return () => {
      active = false;
      window.clearTimeout(timer);
      requestSequence.current++;
    };
  }, [runId, refreshRun]);
  useEffect(() => {
    const onPop = () => {
      const nextId = new URLSearchParams(window.location.search).get("run") ?? "";
      // In-page evidence anchors also emit popstate. Keep the current run and
      // disclosures mounted unless navigation actually selects another run.
      if (nextId === runId) return;
      setRun(null);
      setAudit(null);
      setRunId(nextId);
      setView(viewFromUrl());
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [runId]);
  const openRun = (id: string) => {
    requestSequence.current++;
    setError(null);
    setRun((previous) => previous?.correlation_id === id ? previous : null);
    setRecentOpen(false);
    const url = new URL(window.location.href);
    url.searchParams.set("run", id);
    url.searchParams.delete("view");
    window.history.pushState({}, "", url);
    setRunId(id);
    setView("journey");
    setAudit(null);
  };
  const goHome = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete("run");
    url.searchParams.delete("view");
    window.history.pushState({}, "", url);
    setRunId("");
    setRun(null);
    setAudit(null);
    setError(null);
    setView("journey");
    submissionKey.current = "";
    pendingSubmission.current = null;
    remember("inforsight.pending-submission", null);
  };
  const openArchitecture = (lens?: LensId) => {
    if (lens) {
      const url = new URL(window.location.href);
      url.searchParams.set("lens", lens);
      window.history.replaceState(window.history.state, "", url);
    }
    setView("architecture");
    window.scrollTo({ top: 0 });
  };
  const openModelTimeline = (step?: string) => {
    if (view !== "model") {
      const lens = new URLSearchParams(window.location.search).get("lens") as LensId | null;
      setModelReturn({ view, lens: view === "architecture" ? (lens ?? undefined) : undefined });
    }
    setModelFocus(step);
    setView("model");
    window.scrollTo({ top: 0 });
  };
  const launch = async () => {
    setBusy(true);
    setError(null);
    try {
      const overrides: unknown = JSON.parse(overrideText);
      if (
        !overrides ||
        typeof overrides !== "object" ||
        Array.isArray(overrides)
      )
        throw new Error("Safe inputs must be a JSON object.");
      submissionKey.current ||= crypto.randomUUID();
      remember("inforsight.pending-submission", {
        key: submissionKey.current,
        scenario_id: selected,
        overrides,
      });
      const response = await api<Run>("/runs", {
        method: "POST",
        headers: { "Idempotency-Key": submissionKey.current },
        body: JSON.stringify({ scenario_id: selected, overrides }),
      });
      setRun(response);
      openRun(response.correlation_id);
      submissionKey.current = "";
      pendingSubmission.current = null;
      remember("inforsight.pending-submission", null);
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };
  const retry = async () => {
    if (!run) return;
    setBusy(true);
    setError(null);
    try {
      setRun(
        await api<Run>(
          `/runs/${encodeURIComponent(run.correlation_id)}/retry`,
          {
            method: "POST",
            headers: { "Idempotency-Key": crypto.randomUUID() },
            body: "{}",
          },
        ),
      );
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };
  const verifyAudit = async () => {
    if (!runId) return;
    setAuditBusy(true);
    setError(null);
    try {
      setAudit(await api<Audit>(`/runs/${encodeURIComponent(runId)}/audit`));
    } catch (e) {
      setError(asError(e));
    } finally {
      setAuditBusy(false);
    }
  };
  useEffect(() => {
    if (view === "audit" && runId) void verifyAudit();
  }, [view, runId]); // Audit is verified by its endpoint, never inferred from a badge.
  const picked = catalog?.scenarios.find((s) => s.scenario_id === selected);
  const completed =
    run?.stages.filter(
      (s) => s.status === "completed" || s.status === "abstained",
    ).length ?? 0;
  const stageTotal = run?.stages.length ?? orderedStages.length;
  const inaccessible = error instanceof ApiError && [401, 403, 404, 410].includes(error.status);

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <div className="header-inner">
          <button
            className="brand"
            onClick={goHome}
            aria-label="Inforsight home"
          >
            <span className="brand-mark">
              <Activity size={21} />
            </span>
            Inforsight
            <span className="brand-separator" />
            <span className="brand-subtitle">Interactive demo</span>
          </button>
          <div className="header-right">
            <nav className="header-nav" aria-label="Explore how Inforsight works">
              <button
                type="button"
                className={`header-nav-button ${view === "architecture" ? "active" : ""}`}
                aria-current={view === "architecture" ? "page" : undefined}
                title="Architecture explorer"
                onClick={() => openArchitecture()}
              >
                <Network size={15} aria-hidden="true" />
                <span className="header-nav-label">Architecture</span>
                <span className="sr-only"> explorer</span>
                {!architectureSeen && <span className="new-badge">New</span>}
              </button>
              <button
                type="button"
                className={`header-nav-button ${view === "model" ? "active" : ""}`}
                aria-current={view === "model" ? "page" : undefined}
                title="Model timeline"
                onClick={() => openModelTimeline()}
              >
                <History size={15} aria-hidden="true" />
                <span className="header-nav-label">Model timeline</span>
              </button>
            </nav>
            <span className="environment">
              <span />
              {session ? (session.public_mode ? "Public preview" : "Local Docker") : catalogError ? "Demo unavailable" : "Connecting to demo"}
            </span>
            <span className="fictional-label">
              <LockKeyhole size={13} />
              Fictional policies only
            </span>
          </div>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {session?.public_mode && (
          <div className="visitor-notice content-width" role="note">
            <LockKeyhole size={17} aria-hidden="true" />
            <p>
              <strong>Your fictional cases belong to this browser.</strong>{" "}
              A signed visitor cookie protects your runs at this website address. Run links
              work only with that cookie; clearing it removes access. Cases are temporary.
              Completed runs are retained for up to {session.limits.retention_hours ?? 24} hours.
            </p>
          </div>
        )}
        {view === "model" ? (
          <Suspense
            fallback={
              <div className="content-width">
                <Empty title="Loading the model timeline" icon={History}>
                  Preparing the timeline.
                </Empty>
              </div>
            }
          >
            <ModelTimeline
              backLabel={
                modelReturn.view === "architecture"
                  ? "Back to the architecture"
                  : runId
                    ? "Back to your case"
                    : "All scenarios"
              }
              onBack={() => {
                if (modelReturn.view === "architecture") return openArchitecture(modelReturn.lens);
                setView(modelReturn.view);
                window.scrollTo({ top: 0 });
              }}
              focus={modelFocus}
              onOpenLineage={() => openArchitecture("lineage")}
            />
          </Suspense>
        ) : !runId && view !== "architecture" ? (
          <>
            <section className="hero content-width">
              <div className="hero-copy">
                <p className="eyebrow accent">
                  <span className="tiny-line" />
                  ACCOUNTABLE AI, IN PRACTICE
                </p>
                <h1>
                  From one event.
                  <br />
                  To an informed
                  <br />
                  <span>human decision.</span>
                </h1>
                <p className="hero-description">
                  Inforsight turns fictional policy events into evidence-backed,
                  advisory recommendations—with human review and a verifiable
                  audit trail.
                </p>
                <div className="hero-actions">
                  <a className="button primary" href="#scenarios">
                    Run a fictional case
                    <ArrowRight size={17} />
                  </a>
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => openArchitecture()}
                  >
                    <Network size={16} aria-hidden="true" />
                    Explore the architecture
                  </button>
                </div>
                <div className="hero-assurance">
                  <ShieldCheck size={17} />
                  <span>
                    Modeled risk. Human authority. No customer outreach.
                  </span>
                </div>
              </div>
              <div
                className="hero-map"
                aria-label="Target journey overview, not live execution"
              >
                <div className="map-caption">
                  <span>THE JOURNEY</span>
                  <Badge>Designed for human review</Badge>
                </div>
                <div className="map-path">
                  <div className="map-event">
                    <span className="map-icon">
                      <ArrowUpRight size={21} />
                    </span>
                    <div>
                      <small>START WITH A SIGNAL</small>
                      <strong>A fictional policy event</strong>
                      <span>Safe inputs, one traceable identity</span>
                    </div>
                  </div>
                  <div className="map-connector" />
                  <div className="map-middle">
                    <div>
                      <Activity size={23} />
                      <strong>Understand risk</strong>
                      <span>Snapshot · model · rules</span>
                    </div>
                    <ArrowRight size={19} />
                    <div>
                      <GitBranch size={23} />
                      <strong>Weigh options</strong>
                      <span>Value · capacity · evidence</span>
                    </div>
                  </div>
                  <div className="map-connector" />
                  <div className="map-review">
                    <div className="map-icon">
                      <FileCheck2 size={22} />
                    </div>
                    <div>
                      <small>HUMAN AUTHORITY</small>
                      <strong>You make the decision</strong>
                      <span>The agent provides a draft, or abstains.</span>
                    </div>
                  </div>
                  <div className="map-footer">
                    <Fingerprint size={16} />
                    <span>Every recorded step leaves evidence.</span>
                  </div>
                </div>
              </div>
            </section>
            <section id="scenarios" className="scenario-section">
              <div className="content-width">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">TRY THE SYSTEM</p>
                    <h2>Choose the story you want to follow.</h2>
                  </div>
                  <span className="small muted">
                    Fictional inputs · real backend responses
                  </span>
                </div>
                {catalogError && (
                  <div role="alert" className="notice danger">
                    <Info size={18} />
                    <div>
                      <strong>{requestTitle(catalogError)}</strong>
                      <p>{catalogError.message} No run has started.</p>
                      <button
                        className="text-link"
                        onClick={() => void loadCatalog()}
                      >
                        Check connection again
                      </button>
                    </div>
                  </div>
                )}
                <div
                  className="scenario-grid"
                  role="radiogroup"
                  aria-label="Fictional scenario"
                >
                  {scenarioCopy.map((s, i) => {
                    const backend = catalog?.scenarios.find(
                      (item) => item.scenario_id === s.id,
                    );
                    const enabled = backend?.enabled === true;
                    const Icon = s.icon;
                    return (
                      <button
                        key={s.id}
                        className={`scenario-card ${selected === s.id ? "selected" : ""}`}
                        role="radio"
                        aria-checked={selected === s.id}
                        tabIndex={selected === s.id ? 0 : -1}
                        onKeyDown={(event) => {
                          if (
                            ![
                              "ArrowRight",
                              "ArrowDown",
                              "ArrowLeft",
                              "ArrowUp",
                              "Home",
                              "End",
                            ].includes(event.key)
                          )
                            return;
                          event.preventDefault();
                          const options = Array.from(
                            event.currentTarget.parentElement!.querySelectorAll<HTMLButtonElement>(
                              '[role="radio"]:not(:disabled)',
                            ),
                          );
                          const current = options.indexOf(event.currentTarget);
                          const next =
                            event.key === "Home"
                              ? 0
                              : event.key === "End"
                                ? options.length - 1
                                : (current +
                                    (["ArrowRight", "ArrowDown"].includes(
                                      event.key,
                                    )
                                      ? 1
                                      : -1) +
                                    options.length) %
                                  options.length;
                          options[next]?.focus();
                          options[next]?.click();
                        }}
                        disabled={!enabled || busy}
                        onClick={() => {
                          setSelected(s.id);
                          setOverrideText("{}");
                          submissionKey.current = "";
                          pendingSubmission.current = null;
                          remember("inforsight.pending-submission", null);
                        }}
                      >
                        <div className="scenario-card-top">
                          <span className="scenario-icon">
                            <Icon size={23} />
                          </span>
                          <span className="scenario-number">0{i + 1}</span>
                        </div>
                        <p className="eyebrow">{s.label}</p>
                        <h3>{backend?.title ?? s.title}</h3>
                        <p>{backend?.description ?? s.description}</p>
                        <div className="scenario-card-bottom">
                          {enabled ? (
                            <>
                              <span>
                                {selected === s.id
                                  ? "Selected scenario"
                                  : "Choose scenario"}
                              </span>
                              {selected === s.id ? (
                                <CheckCircle2 size={18} />
                              ) : (
                                <ArrowRight size={18} />
                              )}
                            </>
                          ) : (
                            <>
                              <span>
                                {catalog
                                  ? "Not connected"
                                  : catalogError
                                    ? "Service unavailable"
                                    : "Checking availability"}
                              </span>
                              <LockKeyhole size={15} />
                            </>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
                <div className="launch-panel">
                  <div>
                    <h3>
                      {picked?.enabled
                        ? "Ready when you are."
                        : "Waiting for a connected scenario."}
                    </h3>
                    <p>
                      {picked?.enabled
                        ? "Submit one event and follow what the services actually record."
                        : "A scenario becomes available when its backend is connected."}
                    </p>
                  </div>
                  <button
                    className="button primary"
                    disabled={!picked?.enabled || busy}
                    onClick={() => void launch()}
                  >
                    <Play size={16} />
                    {busy ? "Submitting event…" : "Start this case"}
                    <ArrowRight size={16} />
                  </button>
                </div>
                {pendingSubmission.current && (
                  <div className="notice neutral small">
                    <RotateCcw size={16} />
                    <p>
                      An earlier submission is awaiting acknowledgment. Starting
                      this case again reuses its saved request identity; it does
                      not create a duplicate.
                    </p>
                  </div>
                )}
                <details className="advanced">
                  <summary>
                    <SlidersHorizontal size={16} />
                    Inspect or modify safe inputs
                    <ChevronDown size={16} />
                  </summary>
                  <div className="advanced-body">
                    <p className="small">
                      Only the scenario’s allowlisted inputs are accepted.
                      Unknown fields, unsafe values, and external destinations
                      are rejected by the backend.
                    </p>
                    <Technical
                      value={
                        picked?.inputs ??
                        catalog?.safe_inputs ??
                        picked?.defaults ?? {
                          status: "Scenario input contract is unavailable.",
                        }
                      }
                      label="Scenario input contract"
                    />
                    <label htmlFor="overrides">
                      Optional input overrides (JSON)
                    </label>
                    <textarea
                      id="overrides"
                      className="code-input"
                      value={overrideText}
                      spellCheck={false}
                      onChange={(e) => {
                        setOverrideText(e.target.value);
                        submissionKey.current = "";
                        pendingSubmission.current = null;
                        remember("inforsight.pending-submission", null);
                      }}
                      rows={4}
                      disabled={!picked?.enabled || busy}
                    />
                    <p className="small muted">
                      Leave <code>{"{}"}</code> to use the predefined fictional
                      case.
                    </p>
                  </div>
                </details>
                <form
                  className="resume-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (resume.trim()) openRun(resume.trim());
                  }}
                >
                  <div className="resume-heading">
                    <label htmlFor="resume">
                      <RotateCcw size={16} />
                      Resume a previous run
                    </label>
                    <button
                      type="button"
                      className="recent-runs-trigger"
                      aria-haspopup="dialog"
                      disabled={!session}
                      onClick={() => setRecentOpen(true)}
                    >
                      <Clock3 size={15} />
                      Recent runs
                      {recentRuns.entries.length > 0 && <span className="recent-runs-trigger-count">{recentRuns.entries.length}</span>}
                    </button>
                  </div>
                  <div className="resume-inputs">
                    <input
                      id="resume"
                      value={resume}
                      onChange={(e) => setResume(e.target.value)}
                      placeholder="Paste a correlation ID"
                      autoComplete="off"
                    />
                    <button
                      className="button secondary"
                      disabled={!resume.trim()}
                    >
                      Open run
                      <ArrowRight size={15} />
                    </button>
                  </div>
                  {session?.public_mode && (
                    <p className="small muted">Use the browser and website address that created the run. A correlation ID is a reference, not an access credential.</p>
                  )}
                </form>
                {error && (
                  <div role="alert" className="notice danger">
                    <Info size={18} />
                    <div><strong>{requestTitle(error)}</strong><p>{error.message}</p></div>
                  </div>
                )}
              </div>
            </section>
            <ModelBand onOpen={openModelTimeline} />
            <ArchitectureTeaser onOpen={openArchitecture} />
          </>
        ) : (
          <div className="workspace content-width">
            <div className="workspace-title">
              <div>
                <button className="text-link back" onClick={goHome}>
                  <ArrowLeft size={14} />
                  All scenarios
                </button>
                <p className="eyebrow">
                  {run
                    ? "FICTIONAL CASE · LIVE EVIDENCE"
                    : view === "architecture"
                      ? "INSIDE INFORSIGHT"
                      : "RESUMING YOUR RUN"}
                </p>
                <h1>
                  {view === "architecture" && !runId
                    ? "A clear boundary at every step."
                    : run
                      ? (scenarioCopy.find((s) => s.id === run.scenario_id)
                          ?.title ?? words(run.scenario_id))
                      : inaccessible ? "This case is unavailable here." : "Connecting to your case…"}
                </h1>
              </div>
              {run && (
                <div className="run-summary">
                  <Badge status={run.status}>{words(run.status)}</Badge>
                  <span>
                    {completed} of {stageTotal} stages recorded
                  </span>
                </div>
              )}
            </div>
            {runId && (
              <div className="run-meta">
                <div>
                  <span>Correlation ID</span>
                  <CopyValue value={runId} label="correlation ID" />
                </div>
                <div className={`connection connection-${connection}`}>
                  <span />
                  {connection === "connected"
                    ? (["COMPLETED", "EXPIRED"].includes(run?.status ?? "") ? "Persisted record loaded" : "Reading live backend state")
                    : connection === "loading"
                      ? "Connecting to services"
                      : error instanceof ApiError && [429, 503].includes(error.status)
                        ? "Polling paused by service"
                        : error instanceof ApiError && [401, 403, 404, 410].includes(error.status)
                          ? "Run access unavailable"
                          : "Connection interrupted"}
                </div>
                {run && (
                  <span className="last-updated">
                    Last record {date(run.updated_at)}
                  </span>
                )}
              </div>
            )}
            <nav className="tab-nav" aria-label="Case views">
              {views.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setView(item.id)}
                  className={view === item.id ? "active" : ""}
                  aria-current={view === item.id ? "page" : undefined}
                  disabled={
                    !run && item.id !== "architecture" && item.id !== "journey"
                  }
                >
                  <item.icon size={17} />
                  {item.label}
                  {item.id === "review" &&
                    run?.status === "AWAITING_REVIEW" && (
                      <span className="tab-dot" />
                    )}
                  {item.id === "architecture" && !architectureSeen && (
                    <span className="tab-new" aria-hidden="true">New</span>
                  )}
                </button>
              ))}
            </nav>
            {error && (
              <div role="alert" className="notice danger">
                <Info size={18} />
                <div>
                  <strong>
                    {requestTitle(error)}
                  </strong>
                  <p>{error.message}</p>
                  {runId && !(error instanceof ApiError && [401, 403, 404, 410, 429, 503].includes(error.status)) && (
                    <button
                      className="text-link"
                      onClick={() => void refreshRun(runId)}
                    >
                      Reconnect to this run
                    </button>
                  )}
                  {error instanceof ApiError && [401, 403].includes(error.status) && (
                    <button className="text-link" onClick={() => window.location.assign(window.location.pathname)}>Start a fresh visitor session</button>
                  )}
                  {error instanceof ApiError && [404, 410].includes(error.status) && (
                    <button className="text-link" onClick={goHome}>Choose a new fictional case</button>
                  )}
                </div>
              </div>
            )}
            <div className="sr-only" aria-live="polite">
              {run
                ? `${words(run.status)}. ${completed} of ${stageTotal} stages recorded.`
                : inaccessible ? "Run access is unavailable in this visitor session." : "Connecting to the backend."}
            </div>
            {view === "architecture" ? (
              <Suspense
                fallback={
                  <Empty title="Loading the architecture" icon={Network}>
                    Preparing the diagrams.
                  </Empty>
                }
              >
                <ArchitectureExplorer
                  run={run}
                  session={session}
                  catalog={catalog}
                  catalogError={catalogError}
                  connection={connection}
                  audit={audit}
                  auditBusy={auditBusy}
                  onVerifyAudit={() => void verifyAudit()}
                  onStartCase={() => {
                    goHome();
                    window.setTimeout(() =>
                      document.getElementById("scenarios")?.scrollIntoView({ block: "start" }),
                    );
                  }}
                  notice={session?.public_mode && <PublicPreviewNotice session={session} />}
                />
              </Suspense>
            ) : !run ? (
              <Empty title={inaccessible ? "No accessible run evidence" : "Waiting for the persisted run"}>
                {inaccessible
                  ? "Use the original browser session and website address, or return to the scenarios to start a new fictional case."
                  : "No stage is marked complete until the backend returns its persisted evidence. Run access requires the original visitor session."}
              </Empty>
            ) : (
              <>
                {view === "flow" && (
                  <TransactionFlow
                    key={run.correlation_id}
                    run={run}
                    connection={connection}
                    onReview={() => setView("review")}
                  />
                )}
                {view === "journey" && (
                  <div className="journey-layout">
                    <Panel
                      title="Follow the evidence"
                      eyebrow="LIVE JOURNEY"
                      className="journey-panel"
                    >
                      <p className="panel-intro">
                        Each step reflects a persisted backend result. Open a
                        step to see who produced it and what changed.
                      </p>
                      <div className="architecture-callout">
                        <span className="architecture-callout-icon">
                          <Network size={19} aria-hidden="true" />
                        </span>
                        <div>
                          <h3>Watch this case move through the system</h3>
                          <p>
                            {["COMPLETED", "EXPIRED", "FAILED"].includes(run.status)
                              ? "See where each recorded step ran, from the gateway to the audit journal."
                              : "The architecture view follows this run: each component lights up as the backend records its stage."}
                          </p>
                        </div>
                        <button
                          type="button"
                          className="button secondary"
                          onClick={() => openArchitecture()}
                        >
                          Open the live architecture
                          <ArrowRight size={15} />
                        </button>
                      </div>
                      <ol className="stage-list">
                        {orderedStages.map((key, index) => {
                          const stage = run.stages.find((s) => s.stage === key);
                          const info = stageInfo[key];
                          return (
                            <StageRow
                              key={key}
                              stage={stage}
                              info={info}
                              index={index}
                              stageKey={key}
                            />
                          );
                        })}
                      </ol>
                    </Panel>
                    <aside className="journey-sidebar">
                      <Panel title="Your case at a glance" icon={FileText}>
                        <button
                          className="button secondary full flow-entry-button"
                          onClick={() => setView("flow")}
                        >
                          <Activity size={16} />
                          Explore transaction flow
                          <ArrowRight size={15} />
                        </button>
                        <dl>
                          <Fact
                            label="Scenario"
                            value={words(run.scenario_id)}
                          />
                          <Fact label="Created" value={date(run.created_at)} />
                          <Fact
                            label="Case"
                            value={
                              run.case_id ? (
                                <CopyValue
                                  value={run.case_id}
                                  label="case ID"
                                />
                              ) : (
                                "Awaiting persistence"
                              )
                            }
                          />
                          <Fact
                            label="Event"
                            value={
                              run.event_id ? (
                                <CopyValue
                                  value={run.event_id}
                                  label="event ID"
                                />
                              ) : (
                                "Awaiting acceptance"
                              )
                            }
                          />
                        </dl>
                        <button
                          className="button secondary full"
                          onClick={() => setView("dossier")}
                        >
                          Open case dossier
                          <ArrowRight size={15} />
                        </button>
                      </Panel>
                      <div className="authority-card">
                        <ShieldCheck size={23} />
                        <h3>
                          Advice ends here. <br />
                          Human authority begins.
                        </h3>
                        <p>
                          The model estimates risk. The agent proposes or
                          abstains. Your review records a decision within this
                          fictional demo.
                        </p>
                        <span>
                          <LockKeyhole size={13} />
                          External execution is disabled
                        </span>
                      </div>
                      {run.status === "AWAITING_REVIEW" && (
                        <div className="review-prompt">
                          <Badge status="processing">Your turn</Badge>
                          <h3>The case is ready for review.</h3>
                          <p>Read the evidence, then record your decision.</p>
                          <button
                            className="button primary full"
                            onClick={() => setView("review")}
                          >
                            Review this case
                            <ArrowRight size={15} />
                          </button>
                        </div>
                      )}
                      {run.status === "EXPIRED" && (
                        <Panel title="This review window has ended" icon={Clock3}>
                          <p className="small">The backend expired this unattended run. Recorded evidence remains readable until cleanup; review and retry are unavailable.</p>
                          <button className="button secondary full" onClick={goHome}>Choose a new fictional case</button>
                        </Panel>
                      )}
                      {run.status === "FAILED" && (
                        <Panel title="Processing stopped" icon={Info}>
                          <p className="small">
                            Recorded steps remain available. Retry resumes this
                            run through the backend’s recovery path.
                          </p>
                          <button
                            className="button secondary full"
                            disabled={busy}
                            onClick={() => void retry()}
                          >
                            <RefreshCw size={15} />
                            {busy ? "Requesting retry…" : "Retry this run"}
                          </button>
                        </Panel>
                      )}
                      {run.status === "COMPLETED" && (
                        <div className="review-prompt complete-prompt">
                          <ShieldCheck size={24} />
                          <h3>A decision with a record.</h3>
                          <p>
                            Inspect the persisted decision and the backend’s
                            integrity verification.
                          </p>
                          <button
                            className="button secondary full"
                            onClick={() => setView("audit")}
                          >
                            View audit trail
                            <ArrowRight size={15} />
                          </button>
                        </div>
                      )}
                    </aside>
                  </div>
                )}
                {view === "dossier" && (
                  <Dossier
                    run={run}
                    onReview={() => setView("review")}
                    onModelHistory={() => openModelTimeline()}
                  />
                )}
                {view === "review" && (
                  <Review
                    run={run}
                    onUpdate={setRun}
                    onAudit={() => setView("audit")}
                  />
                )}
                {view === "audit" && (
                  <AuditView
                    audit={audit}
                    run={run}
                    busy={auditBusy}
                    onVerify={() => void verifyAudit()}
                  />
                )}
              </>
            )}
          </div>
        )}
      </main>
      <footer className="site-footer content-width">
        <span className="footer-brand">
          Inforsight<span>Evidence before action.</span>
        </span>
        <span>
          Fictional policies · advisory recommendations · human authority
        </span>
        {session?.public_mode && (
          <button
            ref={cookieNoticeLink}
            className="text-link"
            onClick={() => {
              remember("inforsight.cookie-notice.v1", null);
              setCookieNoticeDismissed(false);
            }}
          >
            Cookie notice
          </button>
        )}
        <button className="text-link" onClick={() => openModelTimeline()}>
          How the model was built
          <ArrowUpRight size={13} />
        </button>
        <button className="text-link" onClick={() => openArchitecture()}>
          System architecture
          <ArrowUpRight size={13} />
        </button>
      </footer>
      <RecentRuns
        open={recentOpen}
        entries={recentRuns.entries}
        persistent={recentRuns.persistent}
        titleFor={(id) => scenarioCopy.find((scenario) => scenario.id === id)?.title ?? words(id)}
        onDismiss={() => setRecentOpen(false)}
        onOpen={openRun}
        onRemove={recentRuns.remove}
        onClear={recentRuns.clear}
      />
      {session?.public_mode && !cookieNoticeDismissed && (
        <section className="cookie-notice" aria-label="Cookie notice">
          <div className="cookie-notice-inner content-width">
            <LockKeyhole size={22} aria-hidden="true" />
            <p>
              <strong>A cookie keeps your fictional cases private.</strong>
              Inforsight uses an essential session cookie to protect your runs and
              let you resume them in this browser. It lasts up to seven days;
              cases may expire sooner. Clearing the cookie removes access to your runs.
            </p>
            <button
              className="button primary"
              onClick={() => {
                remember("inforsight.cookie-notice.v1", true);
                setCookieNoticeDismissed(true);
                cookieNoticeLink.current?.focus({ preventScroll: true });
              }}
            >
              Got it
            </button>
          </div>
        </section>
      )}
    </>
  );
}

function StageRow({
  stage,
  info,
  index,
  stageKey,
}: {
  stage?: Stage;
  info: (typeof stageInfo)[string];
  index: number;
  stageKey: string;
}) {
  const status = stage?.status ?? "waiting";
  const completed = status === "completed" || status === "abstained";
  return (
    <li
      className={`stage-row stage-${status}`}
      id={`stage-${stageKey}`}
      data-testid={`stage-${stageKey}`}
      data-status={status}
    >
      <details>
        <summary>
          <div className="stage-marker">
            <StatusIcon status={status} />
          </div>
          <div className="stage-label">
            <div>
              <span className="stage-number">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3>{info.title}</h3>
            </div>
            <p>
              {status === "abstained"
                ? "The agent abstained. Its reason is recorded below."
                : info.description}
            </p>
          </div>
          <div className="stage-state">
            <Badge status={status}>{stage ? status : "Not connected"}</Badge>
            <span>
              {completed
                ? duration(stage?.duration_ms)
                : status === "processing"
                  ? "Awaiting service result"
                  : status === "waiting"
                    ? stageKey === "decision"
                      ? "Awaiting human review"
                      : stageKey === "audit"
                        ? "Awaiting decision"
                        : "Awaiting previous step"
                    : "See evidence"}
            </span>
          </div>
          <ChevronDown size={15} className="stage-chevron" />
        </summary>
        <div className="stage-evidence">
          <dl className="evidence-grid">
            <Fact
              label="Produced by"
              value={stage?.producer ?? info.component}
            />
            <Fact label="Attempt" value={stage?.attempt ?? "Not started"} />
            <Fact label="Started" value={date(stage?.started_at)} />
            <Fact label="Completed" value={date(stage?.completed_at)} />
          </dl>
          {stage?.error != null && (
            <div className="notice danger small">{text(stage.error)}</div>
          )}
          {Array.isArray(stage?.input_refs) && stage.input_refs.length > 0 && (
            <div className="evidence-links">
              <span>Input evidence</span>
              {stage.input_refs.map((reference: unknown) => {
                const target = text(reference).split("/").pop() ?? "";
                return stageInfo[target] ? (
                  <a
                    key={text(reference)}
                    href={`#stage-${target}`}
                    onClick={() => {
                      const details =
                        document.querySelector<HTMLDetailsElement>(
                          `#stage-${target} > details`,
                        );
                      if (details) details.open = true;
                    }}
                  >
                    {stageInfo[target].title}
                    <ArrowUpRight size={13} />
                  </a>
                ) : (
                  <code key={text(reference)}>{text(reference)}</code>
                );
              })}
            </div>
          )}
          <Technical
            label="Inputs, outputs, and recorded result"
            value={
              stage
                ? {
                    input_refs: stage.input_refs,
                    output_refs: stage.output_refs,
                    evidence: stage.evidence,
                    error: stage.error,
                  }
                : {
                    status: "not_connected",
                    explanation: "This stage has no record from the backend.",
                  }
            }
          />
        </div>
      </details>
    </li>
  );
}

function Dossier({
  run,
  onReview,
  onModelHistory,
}: {
  run: Run;
  onReview: () => void;
  onModelHistory: () => void;
}) {
  const { snapshot, projection, score, rules, allocation, agent } =
    run.artifacts;
  const probability = score?.calibrated_probability;
  const selected = array(allocation?.selected);
  const ruleResults = array(rules?.results);
  const snapshotFacts = snapshot
    ? Object.fromEntries(
        [
          "status",
          "tenure_days",
          "premium_amount_cents",
          "annual_premium_cents",
          "days_past_due",
          "in_grace_period",
        ].map((key) => [key, snapshot[key]]),
      )
    : {};
  const safetyFacts = object(snapshot?.safety);
  const excluded = Array.isArray(projection?.excluded_event_ids)
    ? projection.excluded_event_ids
    : [];
  const drivers = array(score?.top_risk_drivers);
  return (
    <div className="dossier-layout">
      <div className="dossier-main">
        <Panel
          title="The facts at observation time"
          eyebrow="01 / POLICY SNAPSHOT"
          icon={Layers3}
        >
          {snapshot ? (
            <>
              <p className="panel-intro">
                The snapshot is frozen for this run. Evidence arriving after its
                cutoff cannot change what this decision knew.
              </p>
              <dl className="evidence-grid">
                <Fact
                  label="Observation cutoff"
                  value={date(
                    text(
                      snapshot.as_of ??
                        snapshot.as_of_date ??
                        snapshot.observation_time,
                      "",
                    ),
                  )}
                />
                <Fact
                  label="Snapshot identity"
                  value={text(snapshot.snapshot_id ?? snapshot.snapshot_digest)}
                />
              </dl>
              <div className="facts-table">
                {Object.entries(snapshotFacts).map(([key, value]) => (
                  <div key={key}>
                    <span>{words(key)}</span>
                    <strong className={value === null ? "unavailable" : ""}>
                      {value === null || value === undefined
                        ? "Unknown — evidence unavailable"
                        : typeof value === "boolean"
                          ? value
                            ? "Yes"
                            : "No"
                          : text(value)}
                    </strong>
                  </div>
                ))}
              </div>
              <h3 className="subsection-title">Safety evidence</h3>
              <div className="facts-table">
                {Object.entries(safetyFacts).map(([key, value]) => (
                  <div key={key}>
                    <span>{words(key)}</span>
                    <strong className={value === null ? "unavailable" : ""}>
                      {value === null
                        ? "Unknown — evidence unavailable"
                        : value === true
                          ? "Yes"
                          : "No"}
                    </strong>
                  </div>
                ))}
              </div>
              <div className="notice neutral small">
                <Info size={16} />
                <p>
                  {excluded.length} later or otherwise invisible source event
                  {excluded.length === 1 ? "" : "s"} excluded from this
                  observation. The technical evidence lists the exact source
                  identities.
                </p>
              </div>
              <Technical
                value={{
                  snapshot,
                  excluded_event_ids: excluded,
                  feature_lineage: projection?.feature_lineage,
                }}
                label="Full immutable snapshot and provenance"
              />
            </>
          ) : (
            <Empty title="Snapshot not recorded">
              Facts will appear when the observation snapshot is persisted.
            </Empty>
          )}
        </Panel>
        <Panel
          title="What the model sees"
          eyebrow="02 / RELEASED MODEL"
          icon={Activity}
        >
          {score ? (
            <>
              <div className="risk-summary">
                <div>
                  <span className="risk-number">
                    {typeof probability === "number"
                      ? `${(probability * 100).toFixed(1)}`
                      : "—"}
                    <small>%</small>
                  </span>
                  <p>Modeled risk probability</p>
                </div>
                <div>
                  <Badge>
                    {words(
                      score.risk_tier_id ??
                        score.risk_tier ??
                        score.operational_tier,
                    )}
                  </Badge>
                  <p className="small muted">
                    A prediction from a synthetic-data model.
                    <br />
                    It is not a certainty or permission to act.
                  </p>
                </div>
              </div>
              {drivers.length > 0 && (
                <div className="drivers">
                  <h3>Factors increasing modeled risk</h3>
                  {drivers.map((driver, index) => (
                    <div key={index}>
                      <span>{words(driver.feature_name)}</span>
                      <code>
                        {typeof driver.attribution_log_odds === "number"
                          ? `+${driver.attribution_log_odds.toFixed(3)}`
                          : text(driver.attribution_log_odds)}{" "}
                        log-odds
                      </code>
                    </div>
                  ))}
                </div>
              )}
              <div className="notice neutral small">
                <Info size={16} />
                <p>
                  Feature contributions explain the model’s score. They do not
                  establish causes or prove an intervention will work.
                </p>
              </div>
              <button type="button" className="text-link model-history-link" onClick={onModelHistory}>
                <History size={14} aria-hidden="true" />
                How this model was built
                <ArrowRight size={13} aria-hidden="true" />
              </button>
              <Technical
                value={score}
                label="Score, explanations, and model identity"
              />
            </>
          ) : (
            <Empty title="Model result not recorded">
              The released inference service must return a verified scoring
              result.
            </Empty>
          )}
        </Panel>
        <Panel
          title="Which options are eligible?"
          eyebrow="03 / DETERMINISTIC RULES"
          icon={ShieldCheck}
        >
          {rules ? (
            <>
              <p className="panel-intro">
                Eligibility is a rule decision. Missing safety evidence stays
                unknown and can block an option.
              </p>
              <div className="rules-list">
                {ruleResults.map((rule, index) => (
                  <div className="rule" key={index}>
                    <div>
                      <strong>
                        {words(rule.action_type ?? rule.action_id)}
                      </strong>
                      <Badge status={rule.eligible ? "completed" : "blocked"}>
                        {rule.eligible ? "Eligible" : "Ineligible"}
                      </Badge>
                    </div>
                    <p>
                      {Array.isArray(rule.reasons) && rule.reasons.length
                        ? rule.reasons.map(words).join(" · ")
                        : rule.eligible
                          ? "The recorded eligibility checks passed."
                          : "See the recorded rule evidence."}
                    </p>
                  </div>
                ))}
              </div>
              <Technical
                value={rules}
                label="Rule evaluation and reason codes"
              />
            </>
          ) : (
            <Empty title="Rules not evaluated">
              Eligibility appears after the Java rules engine records its
              result.
            </Empty>
          )}
        </Panel>
      </div>
      <aside className="dossier-aside">
        <Panel
          title="How capacity was allocated"
          eyebrow="04 / PORTFOLIO"
          icon={GitBranch}
        >
          {allocation ? (
            <>
              <div className="allocation-choice">
                <small>SELECTED RECOMMENDATION</small>
                <h3>
                  {selected.length
                    ? words(selected[0].action_type ?? selected[0].action_id)
                    : "No action allocated"}
                </h3>
              </div>
              <dl>
                <Fact
                  label="Modeled net value"
                  value={money(allocation.objective_micros)}
                />
                <Fact
                  label="Budget used"
                  value={`${money(allocation.used_money_micros)} / ${money(allocation.budget_micros)}`}
                />
                <Fact
                  label="Personnel used"
                  value={`${text(allocation.used_personnel_seconds)} seconds`}
                />
              </dl>
              <p className="small muted">
                This run allocates across actions for one fictional policy, with
                a $30 budget and 30 minutes of capacity. Value is modeled, not
                measured savings.
              </p>
              <Technical
                value={allocation}
                label="Allocation and constraints"
              />
            </>
          ) : (
            <Empty title="Allocation not recorded">
              The allocator must return a result before a recommendation
              appears.
            </Empty>
          )}
        </Panel>
        <Panel
          title="An advisory draft"
          eyebrow="05 / BOUNDED AGENT"
          icon={Sparkles}
        >
          {agent ? (
            <AgentContent agent={agent} />
          ) : (
            <Empty title="Agent result pending">
              A supported draft or an explicit abstention will appear here.
            </Empty>
          )}
        </Panel>
        <button
          className="button primary full"
          onClick={onReview}
          disabled={!agent}
        >
          Continue to human review
          <ArrowRight size={16} />
        </button>
      </aside>
    </div>
  );
}

function AgentContent({ agent }: { agent: Evidence }) {
  const abstained = agent.status === "ABSTAIN" || agent.status === "ABSTAINED";
  const reasons = Array.isArray(agent.reason_codes) ? agent.reason_codes : [];
  const citations = Array.isArray(agent.procedure_citations)
    ? agent.procedure_citations
    : [];
  const sources = Array.isArray(agent.evidence_source_ids)
    ? agent.evidence_source_ids
    : [];
  const procedure = object(agent.procedure);
  return (
    <>
      <Badge status={abstained ? "abstained" : "completed"}>
        {abstained ? "Agent abstained" : "Draft for human review"}
      </Badge>
      <h3 className="draft-action">
        {abstained
          ? "No supported draft was produced."
          : words(agent.action_id ?? agent.action_type)}
      </h3>
      <p className="small">
        {abstained
          ? "The agent’s evidence boundary stopped this recommendation."
          : "The bounded agent found a cited procedure for this advisory action."}
      </p>
      {reasons.length > 0 && (
        <ul className="reason-list">
          {reasons.map((reason, i) => (
            <li key={i}>{words(reason)}</li>
          ))}
        </ul>
      )}
      {!abstained && procedure.text && (
        <p className="small procedure-excerpt">{text(procedure.text)}</p>
      )}
      {citations.length > 0 && (
        <div className="citation-list">
          <small>PROCEDURE CITATIONS</small>
          {citations.map((citation, i) => (
            <span key={i}>
              <BookOpen size={14} />
              <code>{text(citation)}</code>
            </span>
          ))}
        </div>
      )}
      {sources.length > 0 && (
        <div className="citation-list">
          <small>EVIDENCE SOURCES</small>
          {sources.map((source, i) => (
            <code key={i}>{text(source)}</code>
          ))}
        </div>
      )}
      <Technical value={agent} label="Agent output and authority boundary" />
    </>
  );
}

function Review({
  run,
  onUpdate,
  onAudit,
}: {
  run: Run;
  onUpdate: (run: Run) => void;
  onAudit: () => void;
}) {
  const pendingDecision = useRef(
    stored<{
      key: string;
      decision: "APPROVED" | "REJECTED" | "REQUEST_MORE_INFORMATION";
      rationale: string;
    }>(`inforsight.pending-decision.${run.correlation_id}`),
  );
  const [decision, setDecision] = useState<
    "APPROVED" | "REJECTED" | "REQUEST_MORE_INFORMATION" | null
  >(pendingDecision.current?.decision ?? null);
  const [notes, setNotes] = useState(pendingDecision.current?.rationale ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const decisionKey = useRef(pendingDecision.current?.key ?? "");
  const agent = run.artifacts.agent;
  const recorded = run.artifacts.decision;
  const abstained =
    agent?.status === "ABSTAIN" || agent?.status === "ABSTAINED";
  const ready = run.status === "AWAITING_REVIEW" && Boolean(agent) && !recorded;
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!decision || !ready) return;
    setBusy(true);
    setError(null);
    decisionKey.current ||= crypto.randomUUID();
    remember(`inforsight.pending-decision.${run.correlation_id}`, {
      key: decisionKey.current,
      decision,
      rationale: notes,
    });
    try {
      onUpdate(
        await api<Run>(
          `/runs/${encodeURIComponent(run.correlation_id)}/decision`,
          {
            method: "POST",
            body: JSON.stringify({
              decision,
              expected_case_version: run.case_version,
              idempotency_key: decisionKey.current,
              rationale: notes,
              notes,
              reviewer_id: "fictional-demo-reviewer",
            }),
          },
        ),
      );
      remember(`inforsight.pending-decision.${run.correlation_id}`, null);
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="review-layout">
      <div>
        <Panel
          title="Evidence for your decision"
          eyebrow="HUMAN REVIEW"
          icon={FileCheck2}
        >
          <p className="panel-intro">
            Review the recorded recommendation and its limits. Your decision is
            persisted as a fictional reviewer action.
          </p>
          {agent ? (
            <AgentContent agent={agent} />
          ) : (
            <Empty title="The case is not ready for review">
              The workflow must persist an agent draft or abstention first.
            </Empty>
          )}
          <div className="notice neutral">
            <ShieldCheck size={20} />
            <div>
              <strong>The agent has no action authority.</strong>
              <p>
                Approval records a human decision in this demo. It does not send
                a message, place a call, or change a real policy.
              </p>
            </div>
          </div>
          <Technical
            value={{
              case: run.artifacts.case,
              allocation: run.artifacts.allocation,
              rules: run.artifacts.rules,
            }}
            label="Case, allocated recommendation, and eligibility"
          />
        </Panel>
      </div>
      <Panel
        title={
          recorded ? "Your decision is recorded" : "Make the human decision"
        }
        eyebrow="REVIEWER CONSOLE"
        icon={LockKeyhole}
      >
        {recorded ? (
          <>
            <div className="decision-record">
              <CheckCircle2 size={28} />
              <Badge status="completed">Persisted decision</Badge>
              <h3>{words(recorded.decision)}</h3>
              <p>
                {text(
                  recorded.notes ?? recorded.rationale,
                  "No review note was supplied.",
                )}
              </p>
            </div>
            <Technical value={recorded} label="Committed reviewer record" />
            <button className="button primary full" onClick={onAudit}>
              Inspect the audit trail
              <ArrowRight size={16} />
            </button>
          </>
        ) : (
          <form onSubmit={submit}>
            <fieldset disabled={!ready || busy}>
              <legend>Choose a review outcome</legend>
              <label
                className={`decision-option ${decision === "APPROVED" ? "chosen" : ""}`}
              >
                <input
                  type="radio"
                  name="decision"
                  value="APPROVED"
                  disabled={abstained}
                  checked={decision === "APPROVED"}
                  onChange={() => {
                    setDecision("APPROVED");
                    decisionKey.current = "";
                  }}
                />
                <span>
                  <strong>Approve recommendation</strong>
                  <small>
                    {abstained
                      ? "Unavailable: the agent abstained and proposed no action."
                      : "Record agreement with the advisory result."}
                  </small>
                </span>
                <Check size={17} />
              </label>
              <label
                className={`decision-option ${decision === "REJECTED" ? "chosen" : ""}`}
              >
                <input
                  type="radio"
                  name="decision"
                  value="REJECTED"
                  checked={decision === "REJECTED"}
                  onChange={() => {
                    setDecision("REJECTED");
                    decisionKey.current = "";
                  }}
                />
                <span>
                  <strong>Reject recommendation</strong>
                  <small>
                    Record that this recommendation should not proceed.
                  </small>
                </span>
                <X size={17} />
              </label>
            </fieldset>
            <label
              className={`decision-option ${decision === "REQUEST_MORE_INFORMATION" ? "chosen" : ""}`}
            >
              <input
                type="radio"
                name="decision"
                value="REQUEST_MORE_INFORMATION"
                disabled={!ready || busy}
                checked={decision === "REQUEST_MORE_INFORMATION"}
                onChange={() => {
                  setDecision("REQUEST_MORE_INFORMATION");
                  decisionKey.current = "";
                }}
              />
              <span>
                <strong>Request more information</strong>
                <small>
                  Persist a request for additional evidence within this
                  fictional case.
                </small>
              </span>
              <Info size={17} />
            </label>
            <label className="field-label" htmlFor="review-notes">
              Decision rationale <span>(required)</span>
            </label>
            <textarea
              id="review-notes"
              value={notes}
              onChange={(e) => {
                setNotes(e.target.value);
                decisionKey.current = "";
              }}
              maxLength={500}
              required
              disabled={!ready || busy}
              rows={4}
              placeholder="What informed your decision?"
            />
            <p className="small muted">
              Recorded as a fictional visitor · case version{" "}
              {run.case_version ?? "pending"}
            </p>
            {error && (
              <div role="alert" className="notice danger small">
                <div><strong>{requestTitle(error)}</strong>{error.message}</div>
              </div>
            )}
            <button
              className="button primary full"
              type="submit"
              disabled={!ready || !decision || !notes.trim() || busy}
            >
              {busy ? "Persisting your decision…" : "Record decision"}
              <ArrowRight size={16} />
            </button>
            {!ready && (
              <p className="small muted">
                {run.status === "EXPIRED" ? "This run has expired. It no longer accepts a review decision." : "Review becomes available when all prerequisite stages are recorded."}
              </p>
            )}
          </form>
        )}
      </Panel>
    </div>
  );
}

function AuditView({
  audit,
  run,
  busy,
  onVerify,
}: {
  audit: Audit | null;
  run: Run;
  busy: boolean;
  onVerify: () => void;
}) {
  const entries = audit?.entries ?? [];
  return (
    <div className="audit-layout">
      <div className={`audit-verification ${audit?.valid ? "verified" : ""}`}>
        <span className="audit-seal">
          {audit?.valid ? <ShieldCheck size={31} /> : <Fingerprint size={31} />}
        </span>
        <div>
          <p className="eyebrow">BACKEND INTEGRITY CHECK</p>
          <h2>
            {busy
              ? "Checking the persisted chain…"
              : audit?.valid
                ? "The recorded audit chain is intact."
                : audit
                  ? "Verification did not pass."
                  : "No verification result yet."}
          </h2>
          <p>
            {audit
              ? `${audit.verified_entries ?? entries.length} records checked. ${audit.scope ?? "Verification applies to this local demo run."}`
              : "Verification is requested from the backend; a completed UI step is not proof."}
          </p>
        </div>
        <button className="button secondary" disabled={busy} onClick={onVerify}>
          <RefreshCw size={15} />
          Verify again
        </button>
      </div>
      <div className="audit-grid">
        <Panel
          title="The chain of evidence"
          eyebrow="PERSISTED AUDIT EVENTS"
          icon={Fingerprint}
        >
          {entries.length ? (
            <ol className="audit-entries">
              {entries.map((entry, index) => (
                <li key={text(entry.event_id, String(index))}>
                  <div className="audit-entry-dot">
                    {text(entry.sequence, String(index + 1))}
                  </div>
                  <details>
                    <summary>
                      <div>
                        <strong>
                          {words(entry.event_type ?? entry.stage)}
                        </strong>
                        <span>
                          {date(text(entry.occurred_at, ""))} ·{" "}
                          {text(entry.producer)}
                        </span>
                      </div>
                      <ChevronDown size={16} />
                    </summary>
                    <dl>
                      <Fact label="Event ID" value={text(entry.event_id)} />
                      <Fact
                        label="Parent hash"
                        value={<code>{text(entry.parent_hash)}</code>}
                      />
                      <Fact
                        label="Record hash"
                        value={<code>{text(entry.current_hash)}</code>}
                      />
                    </dl>
                    <Technical
                      value={entry.payload ?? entry}
                      label="Canonical evidence payload"
                    />
                  </details>
                </li>
              ))}
            </ol>
          ) : (
            <Empty title="No audit entries returned">
              The backend has not returned a persisted record chain for this
              run.
            </Empty>
          )}
        </Panel>
        <aside>
          <Panel title="Identity and provenance" icon={FileText}>
            <dl>
              <Fact
                label="Correlation ID"
                value={
                  <CopyValue
                    value={run.correlation_id}
                    label="correlation ID"
                  />
                }
              />
              <Fact label="Case ID" value={text(run.case_id)} />
              <Fact
                label="Case version"
                value={run.case_version ?? "Not persisted"}
              />
              <Fact
                label="Human decision"
                value={words(
                  run.artifacts.decision?.decision ?? "Not recorded",
                )}
              />
              <Fact
                label="Verified head hash"
                value={<code>{text(audit?.head_hash)}</code>}
              />
            </dl>
            <Technical
              value={{
                case: run.artifacts.case,
                decision: run.artifacts.decision,
                verification: audit,
              }}
              label="Case version and verification response"
            />
          </Panel>
          <div className="scope-note">
            <Info size={17} />
            <p>
              A hash chain detects changes within the verified record scope.
              This local demo does not claim an independently anchored or
              externally certified audit log.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function PublicPreviewNotice({ session }: { session: VisitorSession }) {
  return (
    <div className="notice neutral" role="note">
      <LockKeyhole size={20} aria-hidden="true" />
      <div>
        <strong>One public gateway. Isolated visitor sessions.</strong>
        <p>Only this website and its same-origin demo API are exposed. Kafka, PostgreSQL, Java and Python services use a private Docker network. This Mac-hosted preview is available only while the owner’s Mac, Docker stack and tunnel are running.</p>
        <p>Your visitor session expires {date(session.expires_at ?? undefined)}. Run retention can end sooner. A visitor cookie identifies a fictional reviewer; it does not verify a real person’s identity.</p>
        <Technical value={session.limits} label="Inspect public capacity and retention limits" />
      </div>
    </div>
  );
}
