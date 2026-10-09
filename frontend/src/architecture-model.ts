import {
  Activity,
  BarChart3,
  Brain,
  Calculator,
  CalendarClock,
  CheckCircle2,
  CircleX,
  ClipboardCheck,
  Container,
  Cookie,
  Database,
  FileCheck2,
  FileText,
  Filter,
  Fingerprint,
  FlaskConical,
  Gauge,
  Globe,
  Hash,
  Hourglass,
  Laptop,
  Layers3,
  Link2,
  LockKeyhole,
  Package,
  Pause,
  Radio,
  Route,
  Scale,
  Send,
  Server,
  ServerCog,
  ShieldCheck,
  Sigma,
  SlidersHorizontal,
  Sparkles,
  Split,
  Table2,
  Terminal,
  Timer,
  Trash2,
  UserRound,
  Workflow,
  X,
  Check,
  Circle,
  type LucideIcon,
} from "./icons";
import { lensMeta, type LensId } from "./architecture-lenses";

/**
 * Typed architecture model rendered by ArchitectureExplorer. Facts come from the
 * Compose files, nginx.conf, the Java control plane, the Python services and the
 * Flyway migrations; each component lists the sources to check. Geometry is laid
 * out by hand. Connections describe interfaces and workflow order; they are not a
 * capture of network traffic.
 */
export type StageId =
  | "submission"
  | "publication"
  | "ingestion"
  | "snapshot"
  | "score"
  | "rules"
  | "allocation"
  | "case"
  | "agent"
  | "decision"
  | "audit";
export type Deployment = "local" | "public";
export type Tone =
  | "human"
  | "client"
  | "edge"
  | "gateway"
  | "java"
  | "stream"
  | "data"
  | "python"
  | "model"
  | "ops"
  | "security"
  | "state";
export type Side = "top" | "right" | "bottom" | "left";
/** request: HTTP/JDBC call · event: Kafka · data: storage or artifact lineage · control: people and operators. */
export type EdgeKind = "request" | "event" | "data" | "control";
export type GroupVariant =
  | "device"
  | "cloud"
  | "host"
  | "network"
  | "private"
  | "analytics"
  | "zone";
export type LiveProbe =
  | "reviewer"
  | "browser"
  | "edge"
  | "gateway"
  | "control"
  | "kafka"
  | "postgres"
  | "inference"
  | "runtime"
  | "session"
  | "contract"
  | "authority"
  | "integrity"
  | "source"
  | "projection"
  | "snapshot"
  | "features"
  | "score"
  | "rules"
  | "valuation"
  | "allocation"
  | "case"
  | "agent"
  | "decision"
  | "journal"
  | "runStatus"
  | "stageStatus"
  | "caseState"
  | "t_run"
  | "t_outbox"
  | "t_inbox"
  | "t_case"
  | "t_decision"
  | "t_journal"
  | "t_checkpoint"
  | "t_session";

export type Detail = {
  summary: string;
  facts?: [string, string][];
  sections?: { title: string; items: string[] }[];
  source?: string[];
};
export type Column = { name: string; type: string; key?: string };
export type ArchNode = {
  id: string;
  title: string;
  tech: string;
  icon: LucideIcon;
  tone: Tone;
  x: number;
  y: number;
  w: number;
  h: number;
  chips?: string[];
  bullets?: string[];
  columns?: Column[];
  number?: string;
  /** Render the title as a literal value (state names, enum values). */
  mono?: boolean;
  stages?: StageId[];
  /** Run status values that make a lifecycle state current. */
  states?: string[];
  deployments?: Deployment[];
  live?: LiveProbe;
  detail: Detail;
};
export type ArchGroup = {
  id: string;
  label: string;
  caption?: string;
  x: number;
  y: number;
  w: number;
  h: number;
  variant: GroupVariant;
  deployments?: Deployment[];
};
export type ArchEdge = {
  id: string;
  from: string;
  to: string;
  fromSide: Side;
  toSide: Side;
  fromOffset?: number;
  toOffset?: number;
  via?: [number, number][];
  kind: EdgeKind;
  label?: string;
  labelAt?: [number, number];
  twoWay?: boolean;
  stages?: StageId[];
  deployments?: Deployment[];
  detail: Detail;
};
export type ArchStep = {
  title: string;
  text: string;
  /** Edge or node that carries this step's number on the canvas. */
  anchor?: string;
  nodes: string[];
  edges: string[];
  stages?: StageId[];
  deployments?: Deployment[];
};
export type { LensId };
type LensMeta = {
  id: LensId;
  tab: string;
  title: string;
  icon: LucideIcon;
  summary: string;
  reading: string;
};
export type GraphLens = LensMeta & {
  kind: "graph";
  width: number;
  height: number;
  deployable?: boolean;
  stepsTitle: string;
  groups: ArchGroup[];
  nodes: ArchNode[];
  edges: ArchEdge[];
  steps: ArchStep[];
  /** Component that represents a persisted stage when following a live run. */
  focus: Partial<Record<StageId, string>>;
};
export type Participant = {
  id: string;
  title: string;
  tech: string;
  icon: LucideIcon;
  tone: Tone;
  detail: Detail;
};
export type MessageKind = "call" | "return" | "async" | "self";
export type Message = {
  from: string;
  to: string;
  kind: MessageKind;
  label: string;
  detail: Detail;
};
export type BandId = StageId | "session" | "polling";
export type Band = {
  id: BandId;
  title: string;
  caption: string;
  messages: Message[];
};
export type SequenceLens = LensMeta & {
  kind: "sequence";
  participants: Participant[];
  bands: Band[];
};
export type ChainCheck = {
  id: string;
  title: string;
  text: string;
  codes: string[];
};
export type ChainLens = LensMeta & {
  kind: "chain";
  expected: { type: string; producer: string }[];
  checks: ChainCheck[];
  when: string[];
  scope: string[];
};
export type Lens = GraphLens | SequenceLens | ChainLens;

const JAVA = "services/control-plane/src/main/java/com/inforsight/controlplane";
const MIGRATIONS = "services/control-plane/src/main/resources/db/migration";
export const BUNDLE_ID = "inforsight-v6-logistic-platt-20260817";
export const BUNDLE_SHA256 =
  "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656";
export const TOPIC = "inforsight.demo.events.v1";
export const CONSUMER_GROUP = "inforsight-demo-journey-v1";

export const toneLabels: Record<Tone, string> = {
  human: "Human authority",
  client: "Browser",
  edge: "Internet edge",
  gateway: "Gateway",
  java: "Java service",
  stream: "Event streaming",
  data: "Persistence",
  python: "Python service",
  model: "Model",
  ops: "Operations",
  security: "Control",
  state: "State",
};
export const edgeKindLabels: Record<EdgeKind, string> = {
  request: "Request / response",
  event: "Event stream",
  data: "Data and lineage",
  control: "Human or operator control",
};

// ---------------------------------------------------------------------------
// 1. System map: containers, networks, trust boundaries and operators.
// ---------------------------------------------------------------------------
const nginxBase: ArchNode = {
  id: "nginx",
  title: "nginx gateway",
  tech: "nginx stable · assets + reverse proxy",
  icon: Server,
  tone: "gateway" as const,
  x: 768,
  y: 148,
  w: 184,
  h: 124,
  stages: ["submission", "decision"] as StageId[],
  live: "gateway" as const,
  detail: {
    summary:
      "The only container reachable from outside Docker. It serves the built React assets, allowlists exactly the demo API routes, rate-limits them, and proxies them to the Java control plane.",
    facts: [
      ["Image", "nginx:stable-alpine (currently 1.30), assets built with Node 22"],
      ["Allowed API", "/api/v1/demo/ session · scenarios · runs[/id[/retry|decision|audit]]"],
      ["Rate limit", "30 r/s with burst 60 → 429 and Retry-After: 3"],
      ["Request limits", "32 KB bodies · 10 s client timeouts · 60 s upstream read"],
      ["Health", "GET /health (not logged)"],
    ],
    sections: [
      {
        title: "Hardening",
        items: [
          "Every other /api/ path returns 404 before reaching Java.",
          "Content-Security-Policy default-src 'self'; frame-ancestors 'none'; plus nosniff and a strict referrer policy.",
          "API responses carry Cache-Control: no-store, private.",
          "Client Forwarded headers are dropped and X-Forwarded-* values are overwritten, so they never establish identity.",
          "Docker DNS is re-resolved every 5 s, so a recreated control plane is found without a gateway restart.",
        ],
      },
      {
        title: "Page-view logging",
        items: [
          "Only successful HTML GETs of / or /index.html are logged, as {v, id, at}.",
          "No IP address, query string, cookie, referrer or user agent is written.",
          "The file is rotated at 1 MB with 30 archives.",
        ],
      },
    ],
    source: ["frontend/nginx.conf", "frontend/Dockerfile", "frontend/traffic-logrotate.conf"],
  },
};
const javaBase: ArchNode = {
  id: "java",
  title: "Java control plane",
  tech: "Java 21 · Spring Boot 3.5 · virtual threads",
  icon: ServerCog,
  tone: "java" as const,
  x: 753,
  y: 318,
  w: 214,
  h: 200,
  bullets: ["Session filter and REST API", "Outbox → Kafka → inbox worker", "Rules · allocation · audit"],
  stages: [
    "submission",
    "publication",
    "ingestion",
    "rules",
    "allocation",
    "case",
    "decision",
    "audit",
  ] as StageId[],
  live: "control" as const,
  detail: {
    summary:
      "The orchestrator and the only writer of case evidence. It authenticates visitor sessions, accepts submissions through a transactional outbox, runs the Kafka worker, calls both Python services, evaluates eligibility, allocates resources, persists the case, records your decision and verifies the audit chain.",
    facts: [
      ["Build", "Maven → eclipse-temurin:21-jre-alpine, non-root user"],
      ["Profile", "persistence: Flyway migrations + JdbcTemplate"],
      ["Worker", "One SmartLifecycle loop on a virtual thread"],
      ["Journey flags", "journey enabled · HTTP inference · external execution off"],
      ["Scheduler", "Expiry and retention every 60 s (public mode)"],
    ],
    sections: [
      {
        title: "Main classes",
        items: [
          "DemoSessionFilter: route allowlist, signed cookie, quotas, CSRF, ownership.",
          "DemoJourneyController: the /api/v1/demo REST endpoints.",
          "DemoJourneyWorker: outbox → Kafka → inbox → stage pipeline.",
          "EligibilityEngine: deterministic action rules.",
          "PortfolioAllocator: multiple-choice knapsack.",
          "DemoStore: run document, journal, checkpoint and verification.",
          "DemoPublicAccess: sessions, quotas, capacity and retention.",
        ],
      },
      {
        title: "Guarantees",
        items: [
          "Each stage commits its result and journal entry in one transaction under a row lock.",
          "Completed stages are skipped on resume; a failure blocks later stages until retry.",
          "Any dependency response with authorized_to_act: true is rejected.",
        ],
      },
      {
        title: "Known limits",
        items: [
          "One worker: no multi-worker claiming or distributed exactly-once processing.",
          "Broker redelivery and repeated read-only calls remain possible after an interruption.",
        ],
      },
    ],
    source: [
      `${JAVA}/demo/`,
      "services/control-plane/src/main/resources/application.yml",
      "infra/docker/Dockerfile.control-plane",
    ],
  },
};
const kafkaBase: ArchNode = {
  id: "kafka",
  title: "Apache Kafka",
  tech: "cp-kafka 7.9.10 · KRaft",
  icon: Radio,
  tone: "stream" as const,
  x: 492,
  y: 311,
  w: 160,
  h: 214,
  bullets: ["topic inforsight.\u200bdemo.\u200bevents.\u200bv1", "acks=all · manual commits"],
  stages: ["publication", "ingestion"] as StageId[],
  live: "kafka" as const,
  detail: {
    summary:
      "The event bus between accepting a submission and processing it. Java publishes each accepted envelope from the outbox, then consumes it back through a durable consumer group, so processing starts only from a broker-delivered event.",
    facts: [
      ["Topic", `${TOPIC} · 1 partition · replication 1`],
      ["Producer", "acks=all · idempotent · 15 s delivery timeout"],
      ["Consumer", `${CONSUMER_GROUP} · manual commit · earliest`],
      ["Record key", "event_id, which must match the envelope"],
      ["Mode", "KRaft combined broker + controller, no ZooKeeper"],
    ],
    sections: [
      {
        title: "Delivery semantics",
        items: [
          "Offsets are committed only after the inbox row commits; a database outage stops commits.",
          "A record that differs from the persisted outbox copy is quarantined by digest and never processed.",
          "If the broker accepted a record but the acknowledgement record was interrupted, the delivery itself becomes the recorded evidence.",
        ],
      },
      {
        title: "Retention",
        items: [
          "Public preview: no time or size cutoff (retention -1, 16 MB segments).",
          "An operator job advances the low watermark only behind consumed and no-longer-retained offsets.",
        ],
      },
    ],
    source: [
      `${JAVA}/demo/DemoJourneyWorker.java`,
      "infra/docker-compose.yml",
      "infra/docker-compose.public.yml",
    ],
  },
};
const postgresBase: ArchNode = {
  id: "postgres",
  title: "PostgreSQL 16",
  tech: "inforsight_enterprise · demo_* tables",
  icon: Database,
  tone: "data" as const,
  x: 760,
  y: 574,
  w: 200,
  h: 110,
  stages: ["submission", "case", "decision", "audit"] as StageId[],
  live: "postgres" as const,
  detail: {
    summary:
      "The system of record: run documents, the outbox and inbox, the case and its versions, decisions, visitor sessions and quotas, and the append-only SHA-256 journal with its checkpoint.",
    facts: [
      ["Image", "postgres:16-alpine"],
      ["Schema", "Flyway V1–V8 (V6–V8 hold the visitor journey)"],
      ["Public tuning", "shared_buffers 64 MB · max_connections 40 · 512 MB"],
      ["Credentials", "Public: password file on a read-only secrets volume. Local: development value."],
    ],
    sections: [
      {
        title: "Integrity controls",
        items: [
          "Trigger demo_journal_append_only rejects UPDATE and DELETE on journal rows.",
          "The only DELETE exception is verified whole-run retention, in the same transaction as its receipt.",
          "Advisory locks serialize submissions per idempotency key and quota windows; FOR UPDATE row locks serialize stage writers.",
        ],
      },
      {
        title: "Trust boundary",
        items: [
          "The checkpoint lives in the same database. It is not externally anchored or KMS-backed.",
          "A database administrator could rewrite all evidence. This is bounded local integrity.",
        ],
      },
    ],
    source: [
      `${MIGRATIONS}/V6__durable_demo_journey.sql`,
      `${MIGRATIONS}/V7__demo_ingress_quarantine.sql`,
      `${MIGRATIONS}/V8__public_demo_sessions.sql`,
    ],
  },
};
const inferenceBase: ArchNode = {
  id: "inference",
  title: "Inference runtime",
  tech: "Python 3.12 · FastAPI",
  icon: Brain,
  tone: "model" as const,
  x: 1080,
  y: 300,
  w: 160,
  h: 124,
  stages: ["score"] as StageId[],
  live: "inference" as const,
  detail: {
    summary:
      "Serves the released risk model. At startup it verifies the bundle's SHA-256, ID and version. Per request it transforms the 17 raw features, scores, calibrates and explains. It has no authority: every response carries authorized_to_act: false.",
    facts: [
      ["Bundle", `${BUNDLE_ID} · v1.0.0`],
      ["Bundle SHA-256", `${BUNDLE_SHA256.slice(0, 12)}…${BUNDLE_SHA256.slice(-8)}`],
      ["Endpoint used", "POST /v1/score with raw-v6-features"],
      ["Preprocessing", "v6-coefficient-transform-then-bundle-zscore/1.0.0"],
      ["Workers", "1 uvicorn worker · 384 MB in public mode"],
    ],
    sections: [
      {
        title: "Per request",
        items: [
          "The Pydantic contract forbids unknown fields, NaN and infinity.",
          "Coefficient transform (for example tenure/365 clipped to 5) → bundle z-score → one-hot to 28 columns.",
          "L2 logistic logit → Platt calibration (A 0.9618, B −0.0334) → risk tier.",
          "Log-odds attributions and the top risk and protective drivers come from the same response.",
        ],
      },
      {
        title: "Checked by Java",
        items: [
          "Bundle ID, version and digest must equal the pinned release.",
          "policy_id, as_of_date and the preprocessing profile must echo the request.",
          "The probability must be finite and in [0, 1], and the catalog SHA must match the snapshot.",
        ],
      },
      {
        title: "Not publicly routed",
        items: [
          "/v1/model/info, /v1/diagnostics and the batch endpoints exist, but nginx never routes them.",
        ],
      },
    ],
    source: [
      "serving/app.py",
      "serving/preprocessing.py",
      "inference-runtime/src/inforsight_inference/bundle.py",
      "infra/docker/Dockerfile.inference",
    ],
  },
};
const runtimeBase: ArchNode = {
  id: "runtime",
  title: "Demo runtime",
  tech: "Python 3.12 · FastAPI",
  icon: Layers3,
  tone: "python" as const,
  x: 1080,
  y: 470,
  w: 160,
  h: 124,
  stages: ["submission", "snapshot", "allocation", "agent"] as StageId[],
  live: "runtime" as const,
  detail: {
    summary:
      "Stateless adapters over the research code: fictional scenario construction, point-in-time projection, modeled valuation and the bounded review agent. It has no database, credentials, connectors or execution tools.",
    facts: [
      ["Endpoints", "POST /v1/demo/scenario · project · value · draft"],
      ["Observation cutoff", "2026-09-25T12:00:00Z (fictional)"],
      ["Worker identity", "bounded-worker-<uuid> per process"],
      ["Contracts", "Semantic catalog and economics contract v1.0.0"],
    ],
    sections: [
      {
        title: "Endpoints",
        items: [
          "scenario: builds policy, payment and safety source events, including a later recovery event that must stay invisible.",
          "project: rebuilds domain and payment snapshots at the cutoff, the 17 raw V6 features with lineage, and safety facts. snapshot_id is the SHA-256 of the canonical snapshot.",
          "value: modeled effect × annual premium − direct cost per action. Expected value, not realized value.",
          "draft: evidence, procedure and planner checks that cite a versioned procedure or abstain.",
        ],
      },
      {
        title: "Fails closed",
        items: [
          "Unknown request fields are rejected; invalid input returns HTTP 422.",
          "The agent abstains on future, conflicting or missing evidence, injection markers, or no allowed procedure action.",
        ],
      },
    ],
    source: [
      "demo_runtime/app.py",
      "agents/workflow.py",
      "simulator/src/inforsight_simulator/domain_snapshot.py",
      "infra/docker/Dockerfile.demo-runtime",
    ],
  },
};

const systemLens: GraphLens = {
  kind: "graph",
  ...lensMeta("system"),
  title: "Containers, networks, and trust boundaries",
  summary:
    "Every running component, the network it lives on, the ports it exposes, and how a request crosses each boundary.",
  reading:
    "Dashed boxes are trust or network boundaries. Numbers match the dataflow below. Select any component or connection to inspect it.",
  width: 1280,
  height: 858,
  deployable: true,
  stepsTitle: "Dataflow",
  focus: {
    submission: "java",
    publication: "kafka",
    ingestion: "kafka",
    snapshot: "runtime",
    score: "inference",
    rules: "java",
    allocation: "java",
    case: "postgres",
    agent: "runtime",
    decision: "reviewer",
    audit: "postgres",
  },
  groups: [
    { id: "g-device", label: "Visitor device", caption: "browser · same origin only", x: 16, y: 40, w: 214, h: 352, variant: "device" },
    { id: "g-cloud", label: "Cloudflare", caption: "public internet edge", x: 246, y: 40, w: 194, h: 186, variant: "cloud", deployments: ["public"] },
    { id: "g-host", label: "Operator Mac · Docker Desktop", caption: "Compose project inforsight-public", x: 456, y: 16, w: 808, h: 830, variant: "host", deployments: ["public"] },
    { id: "g-host", label: "Developer machine · Docker Desktop", caption: "Compose project inforsight-demo", x: 456, y: 16, w: 808, h: 830, variant: "host", deployments: ["local"] },
    { id: "g-gateway", label: "gateway network", caption: "bridge · publishes 127.0.0.1:3100", x: 666, y: 60, w: 354, h: 146, variant: "network", deployments: ["public"] },
    { id: "g-analytics", label: "analytics network", caption: "bridge · 127.0.0.1:3111 · host only", x: 1036, y: 60, w: 216, h: 146, variant: "analytics", deployments: ["public"] },
    { id: "g-private", label: "private network", caption: "internal: true · no internet route", x: 472, y: 226, w: 780, h: 476, variant: "private", deployments: ["public"] },
    { id: "g-local-net", label: "inforsight-network", caption: "bridge · services publish loopback ports", x: 472, y: 64, w: 780, h: 638, variant: "network", deployments: ["local"] },
    { id: "g-ops", label: "Operator automation", caption: "launchd jobs and CLI · never web-reachable", x: 472, y: 718, w: 780, h: 116, variant: "zone", deployments: ["public"] },
    { id: "g-ops", label: "Developer workflow", caption: "make targets and acceptance harness", x: 472, y: 718, w: 780, h: 116, variant: "zone", deployments: ["local"] },
  ],
  nodes: [
    {
      id: "reviewer",
      title: "You, the reviewer",
      tech: "fictional human authority",
      icon: UserRound,
      tone: "human",
      x: 34,
      y: 84,
      w: 178,
      h: 84,
      stages: ["decision"],
      live: "reviewer",
      detail: {
        summary:
          "Every decision belongs to a person. You choose a fictional scenario, read the persisted evidence, and approve, reject or request more information. The model and agent are advisory, and your decision never contacts a customer.",
        facts: [
          ["Authority", "Records a fictional human decision"],
          ["Identity", "A visitor label, not an authenticated caseworker"],
          ["Options", "Approve · Reject · Request more information"],
          ["Rationale", "Required, up to 500 characters"],
        ],
        sections: [
          {
            title: "Boundaries",
            items: [
              "Approval is unavailable when the agent abstained, and the API rejects it too.",
              "Every outcome keeps authorized_to_act: false and external_execution_enabled: false.",
              "Request more information records an outcome. It does not reopen the case with new evidence.",
            ],
          },
        ],
        source: ["frontend/src/App.tsx (Review)", `${JAVA}/demo/DemoStore.java (decide)`],
      },
    },
    {
      id: "spa",
      title: "React single-page app",
      tech: "React 19 · TypeScript · Vite 6",
      icon: Laptop,
      tone: "client",
      x: 34,
      y: 214,
      w: 178,
      h: 160,
      chips: ["same-origin /api/v1/demo", "polls every 1.5 s"],
      stages: ["submission", "decision"],
      live: "browser",
      detail: {
        summary:
          "The application you are using. It renders persisted backend evidence and never computes scores, stage completion or progress from elapsed time.",
        facts: [
          ["Served by", "nginx, as static assets in the gateway image"],
          ["API surface", "/api/v1/demo/session · scenarios · runs"],
          ["Polling", "One GET at a time every 1.5 s; backs off to 10 s; pauses in hidden tabs"],
          ["Run identity", "?run=<correlation_id> in the address bar"],
        ],
        sections: [
          {
            title: "State and resilience",
            items: [
              "A pending submission keeps its Idempotency-Key in sessionStorage, so a lost response can be retried without a duplicate run.",
              "A response with an older updated_at never overwrites newer state.",
              "Recent runs keep at most 20 IDs with scenario, status and timestamps in localStorage.",
            ],
          },
          {
            title: "Security",
            items: [
              "The visitor cookie is HttpOnly; JavaScript only holds the CSRF token in memory.",
              "Mutations send X-Demo-CSRF; the gateway CSP allows scripts only from this origin.",
              "No fixtures, scores or synthetic timestamps are produced in the browser.",
            ],
          },
        ],
        source: ["frontend/src/App.tsx", "frontend/src/api.ts", "frontend/src/recent-runs.ts"],
      },
    },
    {
      id: "cloudflare",
      title: "Cloudflare edge",
      tech: "HTTPS termination · named tunnel",
      icon: Globe,
      tone: "edge",
      x: 258,
      y: 86,
      w: 170,
      h: 120,
      chips: ["inforsight.aniljonnala.fyi"],
      stages: ["submission", "decision"],
      deployments: ["public"],
      live: "edge",
      detail: {
        summary:
          "The public HTTPS entry point. Cloudflare terminates TLS for inforsight.aniljonnala.fyi and forwards requests through a named tunnel that the Mac dialed out to. The Mac opens no inbound port.",
        facts: [
          ["Plan", "Free, with no billable resource"],
          ["DNS", "Cloudflare DNS with DNSSEC"],
          ["Route", "inforsight.aniljonnala.fyi → http://127.0.0.1:3100"],
          ["Transport", "Tunnel connections initiated from the Mac"],
        ],
        sections: [
          {
            title: "Boundaries",
            items: [
              "Only the gateway hostname is published. The traffic dashboard and every backend port are not routed.",
              "Cloudflare can process request and response traffic, so never enter real personal data.",
              "The preview is available only while the Mac, Docker and the tunnel are running.",
            ],
          },
        ],
        source: ["docs/showcase/public-preview.md", "scripts/public_site.sh"],
      },
    },
    {
      id: "cloudflared",
      title: "cloudflared",
      tech: "launchd daemon · tunnel connector",
      icon: Route,
      tone: "edge",
      x: 488,
      y: 84,
      w: 160,
      h: 108,
      chips: ["→ 127.0.0.1:3100"],
      stages: ["submission", "decision"],
      deployments: ["public"],
      detail: {
        summary:
          "The tunnel connector runs on the Mac as the system LaunchDaemon com.cloudflare.cloudflared. It keeps outbound connections to Cloudflare open and forwards each request to the gateway's loopback port.",
        facts: [
          ["Daemon", "/Library/LaunchDaemons/com.cloudflare.cloudflared.plist"],
          ["Forwards to", "http://127.0.0.1:3100"],
          ["Credential", "Private tunnel token, never printed or committed"],
          ["Managed by", "make public-start and make public-stop"],
        ],
        sections: [
          {
            title: "Operations",
            items: [
              "public-stop disables and unloads the daemon so a reboot stays offline.",
              "public-start enables it and waits for /api/v1/demo/session to answer over HTTPS.",
              "A temporary Quick Tunnel changes hostname and is not used for the named site.",
            ],
          },
        ],
        source: ["scripts/public_site.sh", "scripts/public_demo.py"],
      },
    },
    {
      ...nginxBase,
      chips: ["127.0.0.1:3100 → :80", "gateway + private networks"],
      deployments: ["public"],
    },
    {
      ...nginxBase,
      chips: ["127.0.0.1:3000 → :80"],
      deployments: ["local"],
    },
    {
      id: "traffic",
      title: "Traffic dashboard",
      tech: "Python 3.13 · SQLite · local only",
      icon: BarChart3,
      tone: "ops",
      x: 1052,
      y: 104,
      w: 184,
      h: 90,
      chips: ["127.0.0.1:3111"],
      deployments: ["public"],
      detail: {
        summary:
          "An operator-only page-view counter. It reads the gateway's traffic log from a shared read-only volume every 30 seconds and stores counts in SQLite. It is never routed through the tunnel.",
        facts: [
          ["Image", "python:3.13-alpine running as UID 10001"],
          ["Hardening", "Read-only root FS · cap_drop ALL · 0.5 CPU · 128 MB"],
          ["Retention", "Request IDs 30 days · hourly counts 365 days"],
          ["Meaning", "Page views, not unique people"],
        ],
        sections: [
          {
            title: "Isolation",
            items: [
              "Its analytics network has no route to the backend or the gateway network.",
              "Host and fetch-metadata checks reject DNS rebinding and cross-site requests.",
              "Request-ID deduplication prevents recounting after restarts or log rotation.",
            ],
          },
        ],
        source: ["scripts/traffic_dashboard.py", "infra/docker/Dockerfile.traffic"],
      },
    },
    {
      ...javaBase,
      chips: ["control-plane:8080", "secrets (read-only)"],
      deployments: ["public"],
    },
    {
      ...javaBase,
      chips: ["127.0.0.1:8080", "Flyway V1–V8"],
      deployments: ["local"],
    },
    { ...kafkaBase, chips: ["kafka:29092", "volume kafka_data"], deployments: ["public"] },
    { ...kafkaBase, chips: ["127.0.0.1:9092", "volume kafka_data"], deployments: ["local"] },
    { ...postgresBase, chips: ["postgres:5432", "volume postgres_data"], deployments: ["public"] },
    { ...postgresBase, chips: ["127.0.0.1:5433", "volume postgres_data"], deployments: ["local"] },
    { ...inferenceBase, chips: ["inference-runtime:8000"], deployments: ["public"] },
    { ...inferenceBase, chips: ["127.0.0.1:8000"], deployments: ["local"] },
    { ...runtimeBase, chips: ["demo-runtime:8001", "no DB · no secrets"] },
    {
      id: "maintenance",
      title: "Maintenance agent",
      tech: "LaunchAgent · every 600 s",
      icon: Timer,
      tone: "ops",
      x: 492,
      y: 756,
      w: 214,
      h: 66,
      deployments: ["public"],
      detail: {
        summary:
          "An operator-owned job that keeps Kafka's disk bounded without losing work. It advances the broker's low watermark only below both the committed consumer offset and the earliest offset still referenced by a retained run.",
        facts: [
          ["Command", "scripts/public_demo.py maintain"],
          ["Safe cutoff", "min(committed offset, earliest retained run offset)"],
          ["Tool", "kafka-delete-records through docker compose exec"],
          ["Logs", "maintenance.log in the private state directory"],
        ],
        sections: [
          {
            title: "Safety",
            items: [
              "Deletion is skipped when the committed offset is ambiguous or the cutoff is zero.",
              "The broker fence is read before the database, so later records can only lower the safe bound.",
              "PostgreSQL retention runs inside Java, not in this job.",
            ],
          },
        ],
        source: ["scripts/public_demo.py (maintain, maintenance-install)"],
      },
    },
    {
      id: "operator",
      title: "Operator commands",
      tech: "make public-* · public_demo.py",
      icon: Terminal,
      tone: "ops",
      x: 1046,
      y: 756,
      w: 190,
      h: 66,
      deployments: ["public"],
      detail: {
        summary:
          "The lifecycle of the Mac-hosted preview: secrets, start and stop, rebuild, backup and restore, and deployment manifests. None of it is reachable from the website.",
        facts: [
          ["Start / stop", "make public-start · make public-stop"],
          ["Update", "make public-rebuild builds the branch and checks the public URL"],
          ["Secrets", "256-bit database and signing secrets · host 0600 · volume 0400"],
          ["Backup", "Cold snapshot of Kafka, PostgreSQL and traffic volumes with SHA-256 checksums"],
        ],
        sections: [
          {
            title: "Guardrails",
            items: [
              "Restore refuses existing volumes and pins the recorded image IDs.",
              "Secrets never enter container environment variables; services read files through configtree or *_FILE.",
              "Rebuild refuses an image-pinned restore deployment.",
            ],
          },
        ],
        source: ["scripts/public_site.sh", "scripts/public_demo.py", "Makefile"],
      },
    },
    {
      id: "devops",
      title: "Developer commands",
      tech: "make demo-up · demo-down · demo-reset",
      icon: Terminal,
      tone: "ops",
      x: 492,
      y: 756,
      w: 214,
      h: 66,
      deployments: ["local"],
      detail: {
        summary:
          "Builds and runs the six-service inforsight-demo Compose project on loopback ports. demo-down keeps the named volumes; demo-reset deletes the fictional data.",
        facts: [
          ["Start", "make demo-up → http://localhost:3000"],
          ["Stop", "make demo-down, which keeps volumes"],
          ["Reset", "make demo-reset, which deletes fictional volumes"],
          ["Built images", "frontend · control-plane · inference-runtime · demo-runtime"],
        ],
        source: ["Makefile", "infra/docker-compose.yml", "infra/README.md"],
      },
    },
    {
      id: "acceptance",
      title: "Acceptance harness",
      tech: "make demo-check · demo-browser-check",
      icon: ClipboardCheck,
      tone: "ops",
      x: 1046,
      y: 756,
      w: 190,
      h: 66,
      deployments: ["local"],
      detail: {
        summary:
          "Qualifies the real stack: the API journey with deliberate faults and restarts, then real browser checks through the same gateway. A frontend build alone is not an acceptance pass.",
        facts: [
          ["Recorded result", "22 API, broker, database and fault checks · 17 browser checks"],
          ["Evidence", "artifacts/local-demo/acceptance.json"],
          ["Fault tests", "Interrupt dedicated demo containers and verify recovery"],
        ],
        source: [
          "scripts/run_local_demo_acceptance.py",
          "scripts/local_demo_browser.mjs",
          "docs/showcase/local-demo-acceptance.md",
        ],
      },
    },
  ],
  edges: [
    {
      id: "e-review",
      from: "reviewer",
      to: "spa",
      fromSide: "bottom",
      toSide: "top",
      kind: "control",
      label: "decides",
      stages: ["decision"],
      detail: {
        summary:
          "You act only through the browser: choose a scenario, inspect evidence, and record a decision with a rationale.",
      },
    },
    {
      id: "e-https",
      from: "spa",
      to: "cloudflare",
      fromSide: "right",
      toSide: "bottom",
      fromOffset: -38,
      kind: "request",
      label: "HTTPS :443",
      deployments: ["public"],
      stages: ["submission", "decision"],
      detail: {
        summary:
          "The browser talks only to its own origin. API calls are same-origin fetches with credentials: 'same-origin' and cache: 'no-store'.",
        facts: [
          ["Cookie", "__Host-inforsight_session · HttpOnly · Secure · SameSite=Strict"],
          ["CSRF", "X-Demo-CSRF header on every POST"],
          ["CORS", "None granted"],
        ],
      },
    },
    {
      id: "e-local-http",
      from: "spa",
      to: "nginx",
      fromSide: "right",
      toSide: "left",
      fromOffset: -38,
      via: [
        [440, 256],
        [440, 210],
      ],
      kind: "request",
      label: "HTTP 127.0.0.1:3000",
      labelAt: [338, 256],
      deployments: ["local"],
      stages: ["submission", "decision"],
      detail: {
        summary:
          "Locally the browser reaches the gateway on loopback port 3000. Nothing is reachable from other machines.",
        facts: [
          ["Address", "http://localhost:3000"],
          ["Session", "Non-public mode: the visitor filter is disabled on loopback"],
        ],
      },
    },
    {
      id: "e-tunnel",
      from: "cloudflare",
      to: "cloudflared",
      fromSide: "right",
      toSide: "left",
      fromOffset: -8,
      kind: "request",
      label: "tunnel",
      stages: ["submission", "decision"],
      deployments: ["public"],
      detail: {
        summary:
          "Requests reach the Mac over connections cloudflared opened outbound. No inbound firewall port is opened.",
      },
    },
    {
      id: "e-loopback",
      from: "cloudflared",
      to: "nginx",
      fromSide: "right",
      toSide: "left",
      toOffset: -24,
      kind: "request",
      label: "HTTP :3100",
      stages: ["submission", "decision"],
      deployments: ["public"],
      detail: {
        summary:
          "cloudflared forwards to the loopback-published gateway port. Docker maps 127.0.0.1:3100 to nginx port 80.",
      },
    },
    {
      id: "e-proxy",
      from: "nginx",
      to: "java",
      fromSide: "bottom",
      toSide: "top",
      kind: "request",
      label: "HTTP :8080",
      stages: ["submission", "decision"],
      detail: {
        summary:
          "nginx proxies only the allowlisted demo routes to http://control-plane:8080, with buffering off and a 60 s read timeout.",
        facts: [
          ["Headers", "Host kept · X-Forwarded-For/Host/Proto overwritten · Forwarded cleared"],
          ["Errors", "Gateway rate limit answers 429 with a JSON body and Retry-After: 3"],
        ],
      },
    },
    {
      id: "e-kafka",
      from: "java",
      to: "kafka",
      fromSide: "left",
      toSide: "right",
      kind: "event",
      label: "Kafka :29092",
      twoWay: true,
      stages: ["publication", "ingestion"],
      detail: {
        summary:
          "Java is both producer and consumer. It publishes the outbox envelope, then consumes it back, so processing begins only from a delivered event.",
        facts: [
          ["Produce", `send(${TOPIC}, key = event_id) · acks=all · idempotent`],
          ["Consume", `poll(250 ms) · group ${CONSUMER_GROUP} · max 10 records`],
          ["Commit", "commitSync() only after the inbox row is durable"],
        ],
      },
    },
    {
      id: "e-jdbc",
      from: "java",
      to: "postgres",
      fromSide: "bottom",
      toSide: "top",
      kind: "data",
      label: "JDBC :5432",
      stages: ["submission", "publication", "ingestion", "case", "decision", "audit"],
      detail: {
        summary:
          "Spring JdbcTemplate with transaction templates. Each stage transition updates the run document and appends a hashed journal entry in one transaction.",
        facts: [
          ["Locks", "SELECT … FOR UPDATE per run · pg_advisory_xact_lock for idempotency and quotas"],
          ["Migrations", "Flyway runs V1–V8 at startup"],
        ],
      },
    },
    {
      id: "e-score",
      from: "java",
      to: "inference",
      fromSide: "right",
      toSide: "left",
      fromOffset: -56,
      kind: "request",
      label: "HTTP :8000",
      stages: ["score"],
      detail: {
        summary:
          "POST /v1/score with a 3 s connect and 15 s request timeout. A failure fails the score stage; there is no fallback scorer.",
        facts: [
          ["Request", "policy_id · observation_id · as_of_date · 17 raw features"],
          ["Pinned", `${BUNDLE_ID} · v1.0.0 · SHA-256 ${BUNDLE_SHA256.slice(0, 12)}…`],
        ],
      },
    },
    {
      id: "e-runtime",
      from: "java",
      to: "runtime",
      fromSide: "right",
      toSide: "left",
      fromOffset: 50,
      kind: "request",
      label: "HTTP :8001",
      stages: ["submission", "snapshot", "allocation", "agent"],
      detail: {
        summary:
          "POST /v1/demo/scenario, /project, /value and /draft. Responses must be JSON objects, and any response claiming authorized_to_act: true is rejected.",
        facts: [
          ["Timeouts", "3 s connect · 15 s request"],
          ["Failure", "Submission → 503 with no event accepted; worker stages → failed and retryable"],
        ],
      },
    },
    {
      id: "e-logs",
      from: "nginx",
      to: "traffic",
      fromSide: "right",
      toSide: "left",
      fromOffset: -24,
      toOffset: -14,
      kind: "data",
      label: "logs",
      deployments: ["public"],
      detail: {
        summary:
          "nginx writes privacy-minimal page-view lines to the traffic_logs volume. The dashboard mounts it read-only and collects every 30 seconds.",
      },
    },
    {
      id: "e-maint-kafka",
      from: "maintenance",
      to: "kafka",
      fromSide: "top",
      toSide: "bottom",
      fromOffset: -27,
      kind: "control",
      label: "delete-records",
      deployments: ["public"],
      detail: {
        summary:
          "Every 10 minutes the job reads the committed consumer offset and advances the topic's low watermark no further than any retained run still references.",
      },
    },
    {
      id: "e-maint-pg",
      from: "maintenance",
      to: "postgres",
      fromSide: "right",
      toSide: "bottom",
      kind: "control",
      label: "retained offsets",
      deployments: ["public"],
      detail: {
        summary:
          "Reads the earliest broker offset still referenced by demo_inbox or a retained run's publication evidence, through psql in the PostgreSQL container.",
      },
    },
  ],
  steps: [
    {
      title: "Open the app",
      text: "Cloudflare terminates HTTPS and forwards through the outbound tunnel to nginx, which serves the React assets. The first API call, GET /api/v1/demo/session, sets a signed HttpOnly session cookie and returns a CSRF token.",
      anchor: "e-https",
      nodes: ["spa", "cloudflare", "cloudflared", "nginx", "java"],
      edges: ["e-https", "e-tunnel", "e-loopback", "e-proxy"],
      deployments: ["public"],
    },
    {
      title: "Open the app",
      text: "The browser loads http://localhost:3000 and nginx serves the React assets. On loopback the visitor filter is off, so the session endpoint returns a local session without a cookie.",
      anchor: "e-local-http",
      nodes: ["spa", "nginx", "java"],
      edges: ["e-local-http", "e-proxy"],
      deployments: ["local"],
    },
    {
      title: "Submit a fictional event",
      text: "POST /runs carries an Idempotency-Key and the CSRF header. Java checks the session, quotas and origin, validates exact fields and bounds, asks the demo runtime for fictional source history, then commits the run and its outbox row in one transaction and answers 202 Accepted.",
      anchor: "e-proxy",
      nodes: ["spa", "nginx", "java", "runtime", "postgres"],
      edges: ["e-proxy", "e-runtime", "e-jdbc"],
      stages: ["submission"],
    },
    {
      title: "Round-trip through Kafka",
      text: "The worker publishes the outbox envelope with acks=all, consumes it back, checks it equals the persisted copy, records a deduplicated inbox row, and only then commits the offset.",
      anchor: "e-kafka",
      nodes: ["java", "kafka", "postgres"],
      edges: ["e-kafka", "e-jdbc"],
      stages: ["publication", "ingestion"],
    },
    {
      title: "Freeze point-in-time facts",
      text: "The demo runtime projects the history at the fictional cutoff, 2026-09-25 12:00 UTC, into a content-addressed snapshot and 17 raw features. The later recovery event is excluded and unknown safety facts stay unknown.",
      anchor: "e-runtime",
      nodes: ["java", "runtime"],
      edges: ["e-runtime"],
      stages: ["snapshot"],
    },
    {
      title: "Score with the released model",
      text: "The inference runtime returns a calibrated probability, risk tier and log-odds attributions from the pinned bundle. Java rejects any mismatch in bundle identity, catalog or authority.",
      anchor: "e-score",
      nodes: ["java", "inference"],
      edges: ["e-score"],
      stages: ["score"],
    },
    {
      title: "Decide what is allowed and affordable",
      text: "Java's rules engine evaluates five actions and fails closed. The demo runtime values each candidate with the economics contract, and Java's knapsack selects at most one action within $30 and 1,800 personnel seconds.",
      anchor: "e-runtime",
      nodes: ["java", "runtime"],
      edges: ["e-runtime"],
      stages: ["rules", "allocation"],
    },
    {
      title: "Persist the case and ask the agent",
      text: "Java stores the case with SHA-256 digests of the snapshot, score, rules and allocation, then requests a bounded draft. A draft must cite the allocated action and only snapshot evidence; otherwise the agent abstains.",
      anchor: "e-jdbc",
      nodes: ["java", "postgres", "runtime"],
      edges: ["e-jdbc", "e-runtime"],
      stages: ["case", "agent"],
    },
    {
      title: "Record the human decision",
      text: "You submit a decision with the expected case version. In one transaction Java locks the run, verifies the chain, increments the case version, stores the decision, verifies again and completes the run.",
      anchor: "e-review",
      nodes: ["reviewer", "spa", "nginx", "java", "postgres"],
      edges: ["e-review", "e-proxy", "e-jdbc"],
      stages: ["decision", "audit"],
    },
    {
      title: "Show only persisted evidence",
      text: "The app polls GET /runs/{id} every 1.5 s, one request at a time, backing off to 10 s on errors and pausing in hidden tabs. Every displayed step is a committed backend record.",
      anchor: "e-proxy",
      nodes: ["spa", "nginx", "java", "postgres"],
      edges: ["e-proxy", "e-jdbc"],
    },
    {
      title: "Operate the preview",
      text: "nginx appends page-view lines to a shared volume that the isolated dashboard counts every 30 s. A LaunchAgent advances Kafka's low watermark every 10 minutes without deleting unconsumed or retained work.",
      anchor: "e-logs",
      nodes: ["nginx", "traffic", "maintenance", "kafka", "postgres"],
      edges: ["e-logs", "e-maint-kafka", "e-maint-pg"],
      deployments: ["public"],
    },
    {
      title: "Qualify the stack",
      text: "make demo-check runs the API journey with deliberate container faults and restarts; make demo-browser-check drives a real browser through the same gateway and records the evidence.",
      anchor: "acceptance",
      nodes: ["devops", "acceptance"],
      edges: [],
      deployments: ["local"],
    },
  ],
};

// ---------------------------------------------------------------------------
// 2. Request sequence: every hop of one run, grouped by persisted stage.
// ---------------------------------------------------------------------------
const sequenceLens: SequenceLens = {
  kind: "sequence",
  ...lensMeta("sequence"),
  title: "One run, message by message",
  summary:
    "The exact calls between the browser, gateway, Java, Kafka, PostgreSQL and the Python services, grouped by the eleven persisted stages.",
  reading:
    "Solid arrows are calls, dashed arrows are responses, and open arrows are Kafka events. Loops are work inside one component. Select a message for its contract.",
  participants: [
    {
      id: "browser",
      title: "Browser",
      tech: "React SPA",
      icon: Laptop,
      tone: "client",
      detail: systemLens.nodes.find((node) => node.id === "spa")!.detail,
    },
    { id: "nginx", title: "nginx", tech: "gateway", icon: Server, tone: "gateway", detail: nginxBase.detail },
    {
      id: "api",
      title: "Java API",
      tech: "filter + controller",
      icon: ServerCog,
      tone: "java",
      detail: {
        summary:
          "DemoSessionFilter and DemoJourneyController handle every browser request on the Java side: session, quota, CSRF and ownership checks, then the REST contract.",
        source: [`${JAVA}/demo/DemoSessionFilter.java`, `${JAVA}/demo/DemoJourneyController.java`],
      },
    },
    {
      id: "worker",
      title: "Java worker",
      tech: "virtual thread",
      icon: Workflow,
      tone: "java",
      detail: {
        summary:
          "DemoJourneyWorker is a single SmartLifecycle loop. Each pass publishes pending outbox rows, polls Kafka for 250 ms, records deliveries, then advances every resumable run stage by stage.",
        source: [`${JAVA}/demo/DemoJourneyWorker.java`],
      },
    },
    { id: "postgres", title: "PostgreSQL", tech: "demo_* + journal", icon: Database, tone: "data", detail: postgresBase.detail },
    { id: "kafka", title: "Kafka", tech: "demo topic", icon: Radio, tone: "stream", detail: kafkaBase.detail },
    { id: "runtime", title: "demo-runtime", tech: "FastAPI :8001", icon: Layers3, tone: "python", detail: runtimeBase.detail },
    { id: "inference", title: "inference", tech: "FastAPI :8000", icon: Brain, tone: "model", detail: inferenceBase.detail },
  ],
  bands: [
    {
      id: "session",
      title: "Session bootstrap",
      caption: "Page load, before any run",
      messages: [
        {
          from: "browser",
          to: "nginx",
          kind: "call",
          label: "GET /api/v1/demo/session",
          detail: {
            summary:
              "The first API call. The CSRF token is held in memory; the session cookie itself is HttpOnly and invisible to JavaScript.",
          },
        },
        {
          from: "nginx",
          to: "api",
          kind: "call",
          label: "proxy · allowlisted route",
          detail: {
            summary:
              "nginx matches the exact demo route pattern and proxies to control-plane:8080. Every other /api/ path is answered with 404 at the gateway.",
          },
        },
        {
          from: "api",
          to: "postgres",
          kind: "call",
          label: "INSERT demo_session (public mode)",
          detail: {
            summary:
              "In public mode a missing or invalid cookie on a bootstrap GET issues a new session row, bounded by a global sessions-per-hour quota.",
            facts: [
              ["Token", "session_id.expiry.HMAC-SHA256(secret, 'cookie:'+payload)"],
              ["Lifetime", "7 days, also checked against the database row"],
            ],
          },
        },
        {
          from: "api",
          to: "browser",
          kind: "return",
          label: "Set-Cookie · csrf_token · limits",
          detail: {
            summary:
              "The response sets __Host-inforsight_session (HttpOnly, Secure, SameSite=Strict) and returns the CSRF token, a session tag, the expiry and the public limits.",
          },
        },
      ],
    },
    {
      id: "submission",
      title: "Event submitted",
      caption: "Synchronous request · 202 Accepted",
      messages: [
        {
          from: "browser",
          to: "nginx",
          kind: "call",
          label: "POST /runs · Idempotency-Key · X-Demo-CSRF",
          detail: {
            summary:
              "Body: {scenario_id, overrides}. The key is a browser UUID saved in sessionStorage until the response arrives, so a retry reuses it.",
            facts: [
              ["Allowed overrides", "premium_amount_cents 1,000–100,000 · delay_days 1–45"],
              ["Scenarios", "late-payment · missing-safety-evidence · agent-abstention"],
            ],
          },
        },
        {
          from: "nginx",
          to: "api",
          kind: "call",
          label: "limit_req 30 r/s · proxy :8080",
          detail: {
            summary:
              "The shared gateway limit absorbs bursts. Durable per-visitor and global quotas are enforced in Java and PostgreSQL.",
          },
        },
        {
          from: "api",
          to: "api",
          kind: "self",
          label: "cookie HMAC · quota · CSRF · origin",
          detail: {
            summary:
              "DemoSessionFilter rejects encoded or dotted paths, verifies the signed cookie against its database row, consumes request quotas, and requires both the CSRF token and an Origin that matches Host for mutations.",
            facts: [
              ["Rejections", "401 session · 403 CSRF · 404 route or owner · 429 quota"],
            ],
          },
        },
        {
          from: "api",
          to: "runtime",
          kind: "call",
          label: "POST /v1/demo/scenario",
          detail: {
            summary:
              "Java creates the run_, evt_ and pol_ identities and asks the demo runtime for fictional source history. If the runtime is unavailable, the API answers 503 and no event is accepted.",
          },
        },
        {
          from: "runtime",
          to: "api",
          kind: "return",
          label: "source history · as_of 2026-09-25T12:00Z",
          detail: {
            summary:
              "Policy issuance, five on-time payments, the submitted late payment, a later recovery event, and safety facts. The response must be fictional and echo the event ID.",
          },
        },
        {
          from: "api",
          to: "postgres",
          kind: "call",
          label: "TX: advisory lock · demo_run + demo_outbox",
          detail: {
            summary:
              "pg_advisory_xact_lock on the scoped idempotency key, a replay check, INSERT demo_run (status WAITING) and INSERT demo_outbox with the envelope, plus journal entry 1, submission.completed.",
            facts: [["Envelope", "schema inforsight.demo.event/1.0.0 · event_type fictional.policy_event_submitted"]],
          },
        },
        {
          from: "api",
          to: "browser",
          kind: "return",
          label: "202 Accepted · run document",
          detail: {
            summary:
              "The browser stores the correlation ID in the URL and starts polling. A repeated key with the same body replays the stored run; a different body conflicts with 409.",
          },
        },
      ],
    },
    {
      id: "publication",
      title: "Event published",
      caption: "Asynchronous · transactional outbox",
      messages: [
        {
          from: "worker",
          to: "postgres",
          kind: "call",
          label: "pending outbox (LIMIT 10) · publication.processing",
          detail: {
            summary:
              "Unpublished envelopes with fewer than 3 attempts are read in creation order. The attempt counter increments before sending.",
          },
        },
        {
          from: "worker",
          to: "kafka",
          kind: "async",
          label: `send ${TOPIC} · key=event_id · acks=all`,
          detail: {
            summary:
              "The idempotent producer waits up to 20 s for the broker acknowledgement. A failure marks publication failed and blocks the later stages.",
          },
        },
        {
          from: "kafka",
          to: "worker",
          kind: "return",
          label: "RecordMetadata · partition · offset · timestamp",
          detail: { summary: "The broker receipt becomes the publication evidence, with the envelope SHA-256." },
        },
        {
          from: "worker",
          to: "postgres",
          kind: "call",
          label: "published_at · publication.completed",
          detail: { summary: "The outbox row is marked published and the stage completes in the same transaction." },
        },
      ],
    },
    {
      id: "ingestion",
      title: "Event received",
      caption: "Consumer group · durable inbox",
      messages: [
        {
          from: "kafka",
          to: "worker",
          kind: "async",
          label: `poll(250 ms) · group ${CONSUMER_GROUP}`,
          detail: { summary: "Auto-commit is off and at most 10 records are returned per poll." },
        },
        {
          from: "worker",
          to: "postgres",
          kind: "call",
          label: "envelope = outbox? · INSERT demo_inbox ON CONFLICT DO NOTHING",
          detail: {
            summary:
              "The delivered envelope must equal the persisted outbox envelope and the record key must equal its event_id. Duplicates insert nothing. Invalid records go to demo_ingress_quarantine by digest.",
          },
        },
        {
          from: "worker",
          to: "kafka",
          kind: "call",
          label: "commitSync() after the durable receipt",
          detail: {
            summary:
              "If PostgreSQL is unavailable the exception escapes before the commit, so the record is delivered again rather than lost.",
          },
        },
      ],
    },
    {
      id: "snapshot",
      title: "Policy snapshot",
      caption: "Point-in-time projection",
      messages: [
        {
          from: "worker",
          to: "runtime",
          kind: "call",
          label: "POST /v1/demo/project · history · as_of",
          detail: { summary: "Sends the persisted source history and the fictional cutoff." },
        },
        {
          from: "runtime",
          to: "worker",
          kind: "return",
          label: "snapshot_id · 17 features · excluded event IDs",
          detail: {
            summary:
              "The snapshot is content-addressed (SHA-256 of its canonical JSON). Java checks the policy identity and that a snapshot_id is present before committing.",
          },
        },
        {
          from: "worker",
          to: "postgres",
          kind: "call",
          label: "snapshot.completed · projection artifact",
          detail: { summary: "Stores the projection and snapshot artifacts and their journal entry." },
        },
      ],
    },
    {
      id: "score",
      title: "Modeled risk",
      caption: "Released model over HTTP",
      messages: [
        {
          from: "worker",
          to: "inference",
          kind: "call",
          label: "POST /v1/score · raw-v6-features",
          detail: {
            summary:
              "observation_id is the correlation ID; as_of_date is the snapshot cutoff; the preprocessing profile is v6-coefficient-transform-then-bundle-zscore/1.0.0.",
          },
        },
        {
          from: "inference",
          to: "worker",
          kind: "return",
          label: "calibrated_probability · tier · attributions",
          detail: { summary: "Includes raw and calibrated logits, review-queue eligibility, and authorized_to_act: false." },
        },
        {
          from: "worker",
          to: "worker",
          kind: "self",
          label: "pin bundle ID · version · SHA-256 · catalog",
          detail: {
            summary:
              "Any mismatch raises RELEASED_MODEL_IDENTITY_OR_AUTHORITY_MISMATCH or MODEL_SNAPSHOT_CATALOG_MISMATCH and fails the stage.",
          },
        },
      ],
    },
    {
      id: "rules",
      title: "Eligibility rules",
      caption: "In-process, deterministic",
      messages: [
        {
          from: "worker",
          to: "worker",
          kind: "self",
          label: "EligibilityEngine → 5 actions, fail-closed",
          detail: {
            summary:
              "Builds a PolicyContext from the projection. Unknown safety evidence disqualifies every action except abstain; legal hold, an active claim or a dispute freeze does the same.",
            facts: [["Rules version", "java-eligibility/1.0.0"]],
          },
        },
      ],
    },
    {
      id: "allocation",
      title: "Portfolio allocation",
      caption: "Modeled value under capacity",
      messages: [
        {
          from: "worker",
          to: "runtime",
          kind: "call",
          label: "POST /v1/demo/value · snapshot · score · rules",
          detail: { summary: "The runtime re-validates the snapshot identity and the score's authority and catalog before valuing." },
        },
        {
          from: "runtime",
          to: "worker",
          kind: "return",
          label: "candidates · cost · seconds · net value",
          detail: { summary: "One candidate per action with direct cost, personnel seconds and net expected value in USD micros." },
        },
        {
          from: "worker",
          to: "worker",
          kind: "self",
          label: "multiple-choice knapsack · $30 · 1,800 s",
          detail: {
            summary:
              "Only candidates eligible in both Java's rules and the valuation are considered. At most one action is selected, otherwise selected_action is abstain.",
            facts: [["Allocator", "java-multiple-choice-knapsack/1.1.0"]],
          },
        },
      ],
    },
    {
      id: "case",
      title: "Case persisted",
      caption: "Evidence bound by digest",
      messages: [
        {
          from: "worker",
          to: "postgres",
          kind: "call",
          label: "INSERT demo_case · 4 evidence digests",
          detail: {
            summary:
              "The case record holds SHA-256 digests of the snapshot, score, rules and allocation, the bundle digest and the recommended action, with state AWAITING_REVIEW and case_version 0.",
          },
        },
      ],
    },
    {
      id: "agent",
      title: "Advisory draft",
      caption: "Bounded agent",
      messages: [
        {
          from: "worker",
          to: "runtime",
          kind: "call",
          label: "POST /v1/demo/draft · case · evidence",
          detail: { summary: "Sends the case identity and version with the snapshot, score, rules and allocation." },
        },
        {
          from: "runtime",
          to: "worker",
          kind: "return",
          label: "DRAFT_FOR_REVIEW or ABSTAIN · citations",
          detail: {
            summary:
              "A draft names one action and cites fictional-local-review@1.0.0 and source event IDs; an abstention lists reason codes and no action.",
          },
        },
        {
          from: "worker",
          to: "postgres",
          kind: "call",
          label: "binding checks · status AWAITING_REVIEW",
          detail: {
            summary:
              "Java requires the same case, version and snapshot, no authority, human review required, the allocated action, the trusted citation, and evidence inside the snapshot.",
          },
        },
      ],
    },
    {
      id: "polling",
      title: "Polling",
      caption: "Throughout the run",
      messages: [
        {
          from: "browser",
          to: "api",
          kind: "call",
          label: "GET /runs/{id} via nginx · every 1.5 s",
          detail: {
            summary:
              "Serial reads: the next poll is scheduled only after the previous one finishes. Errors back off up to 10 s, a Retry-After is honored, and hidden tabs pause.",
          },
        },
        {
          from: "api",
          to: "postgres",
          kind: "call",
          label: "SELECT document · owner check",
          detail: { summary: "In public mode the run must belong to the requesting session; otherwise 404, or 410 after retention." },
        },
        {
          from: "api",
          to: "browser",
          kind: "return",
          label: "persisted run · no-store",
          detail: { summary: "The browser keeps the newer of two documents by updated_at and stops polling at COMPLETED or EXPIRED." },
        },
      ],
    },
    {
      id: "decision",
      title: "Human decision",
      caption: "One database transaction",
      messages: [
        {
          from: "browser",
          to: "nginx",
          kind: "call",
          label: "POST /runs/{id}/decision · expected_case_version",
          detail: {
            summary:
              "Body: decision, expected_case_version, idempotency_key, rationale, notes and reviewer_id. In public mode Java replaces reviewer_id with the visitor tag.",
          },
        },
        {
          from: "nginx",
          to: "api",
          kind: "call",
          label: "proxy · CSRF and owner checks",
          detail: { summary: "The same filter chain as submission, plus the decisions-per-hour quota." },
        },
        {
          from: "api",
          to: "postgres",
          kind: "call",
          label: "FOR UPDATE · replay · version · verify chain",
          detail: {
            summary:
              "The run must be AWAITING_REVIEW and the expected version current (else 409). The journal is verified before the decision is accepted. Approval requires an allocated, non-abstained draft.",
          },
        },
        {
          from: "api",
          to: "postgres",
          kind: "call",
          label: "case_version + 1 · demo_case · decision.completed",
          detail: { summary: "The case state becomes HUMAN_APPROVED, REJECTED or MORE_INFORMATION_REQUESTED." },
        },
      ],
    },
    {
      id: "audit",
      title: "Audit verified",
      caption: "Same transaction as the decision",
      messages: [
        {
          from: "api",
          to: "postgres",
          kind: "call",
          label: "recompute SHA-256 chain · checkpoint · bindings",
          detail: {
            summary:
              "The verifier runs against the pending decision. If it fails, the whole transaction rolls back and no decision is stored.",
          },
        },
        {
          from: "api",
          to: "browser",
          kind: "return",
          label: "200 · COMPLETED · verified head hash",
          detail: { summary: "demo_decision stores the response so a retried request with the same key replays it." },
        },
        {
          from: "browser",
          to: "api",
          kind: "call",
          label: "GET /runs/{id}/audit · independent re-check",
          detail: { summary: "The Audit trail view asks the backend to verify again and returns every journal entry." },
        },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// 3. Data and model lineage: offline model factory and per-run evidence chain.
// ---------------------------------------------------------------------------
const OFF_Y = 84;
const OFF_W = 128;
const offX = (index: number) => 26 + index * 150;
const ONLINE_W = 266;
const colX = (column: number) => 26 + column * 300;
const rowY = (row: number) => 314 + row * 160;
const lineageLens: GraphLens = {
  kind: "graph",
  ...lensMeta("lineage"),
  title: "From simulated history to a verified decision",
  summary:
    "How the released model was built once, offline, and how every run turns fictional events into content-addressed evidence.",
  reading:
    "The top lane ran once to produce the model bundle. The lower lane runs for every case. Bound to a run, each artifact shows its recorded value.",
  width: 1240,
  height: 800,
  stepsTitle: "Lineage",
  focus: {
    submission: "o-source",
    snapshot: "o-snapshot",
    score: "o-score",
    rules: "o-rules",
    allocation: "o-allocation",
    case: "o-case",
    agent: "o-agent",
    decision: "o-decision",
    audit: "o-journal",
  },
  groups: [
    { id: "g-offline", label: "Offline model factory", caption: "built once · versioned · released as one file", x: 12, y: 30, w: 1216, h: 196, variant: "zone" },
    { id: "g-online", label: "Per-run evidence chain", caption: "every visitor case · each artifact persisted and hashed", x: 12, y: 258, w: 1216, h: 528, variant: "private" },
  ],
  nodes: [
    {
      id: "l-sim",
      number: "A",
      title: "v6 simulator",
      tech: "bounded sigmoid hazard",
      icon: FlaskConical,
      tone: "model",
      x: offX(0),
      y: OFF_Y,
      w: OFF_W,
      h: 116,
      chips: ["λ ≤ 0.15 · 20 seeds"],
      detail: {
        summary:
          "Generation v6 of the clean-room policy simulator. A bounded logistic hazard link, λ(t) = λmax·σ(z), caps monthly hazard at 0.15 while keeping a learnable signal. 20 of 20 acceptance seeds passed with a median AUC of 0.7031.",
        facts: [
          ["History", "v1–v5 failed or stopped; v6 proceeded"],
          ["Decisions", "ADR 0012 · statistical protocol 3.1.0 (ADR 0013)"],
          ["Data", "Fully synthetic, fictional identities"],
        ],
        source: ["simulator/src/inforsight_simulator/v6_corpus.py", "docs/experiments/iteration-ledger.md"],
      },
    },
    {
      id: "l-events",
      number: "B",
      title: "Event streams",
      tech: "JSON Schema 2020-12",
      icon: Radio,
      tone: "model",
      x: offX(1),
      y: OFF_Y,
      w: OFF_W,
      h: 116,
      chips: ["dual time"],
      detail: {
        summary:
          "Immutable, versioned event envelopes with dual time: when a fact took effect and when it was ingested. Streams cover policy lifecycle, billing and payment, customer service and safety facts.",
        facts: [
          ["Contracts", "data-contracts/*.schema.json"],
          ["Time model", "effective_at and ingested_at on every event"],
        ],
        source: ["data-contracts/", "docs/adr/0015-canonical-dual-time-domain-snapshot.md"],
      },
    },
    {
      id: "l-observations",
      number: "C",
      title: "Observations",
      tech: "as-of cutoffs · 90-day label",
      icon: CalendarClock,
      tone: "model",
      x: offX(2),
      y: OFF_Y,
      w: OFF_W,
      h: 116,
      chips: ["leakage guards"],
      detail: {
        summary:
          "Point-in-time observation records. Features use only events visible at the cutoff, and the label is lapse or surrender within the next 90 days. Leakage and simulator-shortcut guards run before fitting.",
        facts: [
          ["Label", "Lapse or surrender within 90 days"],
          ["Guards", "Leakage and shortcut diagnostics"],
        ],
        source: ["simulator/src/inforsight_simulator/observations.py", "simulator/src/inforsight_simulator/leakage.py"],
      },
    },
    {
      id: "l-splits",
      number: "D",
      title: "Temporal splits",
      tech: "policy-aware",
      icon: Split,
      tone: "model",
      x: offX(3),
      y: OFF_Y,
      w: OFF_W,
      h: 116,
      chips: ["8,782 test rows"],
      detail: {
        summary:
          "Training, validation and test sets are separated by policy and by time, so one policy never informs both training and evaluation.",
        facts: [["Evaluation set", "8,782 observations from 1,440 policies"]],
        source: ["simulator/src/inforsight_simulator/splitting.py"],
      },
    },
    {
      id: "l-features",
      number: "E",
      title: "Feature pipeline",
      tech: "17 features → 28 columns",
      icon: SlidersHorizontal,
      tone: "model",
      x: offX(4),
      y: OFF_Y,
      w: OFF_W,
      h: 116,
      chips: ["train-only z-score"],
      detail: {
        summary:
          "13 numeric and 4 categorical features. Numeric features are z-scored with training statistics only; categoricals are one-hot encoded with an explicit __unknown__ column.",
        facts: [
          ["Numeric", "tenure, premium, recent delay, failed payments, retries, recoveries, arrears, on-time rate, payment count, notices, contacts, 2 missingness flags"],
          ["Categorical", "product_type · billing_frequency · notice_category · contact_category"],
        ],
        source: ["simulator/src/inforsight_simulator/preprocessing.py", "simulator/src/inforsight_simulator/features.py"],
      },
    },
    {
      id: "l-model",
      number: "F",
      title: "Logistic model",
      tech: "L2 · C 1.0 · liblinear",
      icon: Sigma,
      tone: "model",
      x: offX(5),
      y: OFF_Y,
      w: OFF_W,
      h: 116,
      chips: ["AUC 0.6998"],
      detail: {
        summary:
          "A deliberately simple, interpretable baseline: L2-regularized logistic regression with seed 20260817. A boosted comparison model was evaluated and not released.",
        facts: [
          ["ROC AUC", "0.6998 (95% CI 0.6847–0.7153)"],
          ["Average precision", "0.2765"],
          ["Brier score", "0.1211"],
        ],
        source: ["simulator/src/inforsight_simulator/modeling.py", "MODEL_CARD.md"],
      },
    },
    {
      id: "l-calibration",
      number: "G",
      title: "Platt calibration",
      tech: "A 0.9618 · B −0.0334",
      icon: Gauge,
      tone: "model",
      x: offX(6),
      y: OFF_Y,
      w: OFF_W,
      h: 116,
      chips: ["ECE 0.0115"],
      detail: {
        summary:
          "Platt scaling maps the logit to a calibrated probability, p = σ(A·z + B). Calibration matters because review queues and valuation use probabilities, not just ranks.",
        facts: [
          ["Calibration slope", "0.9498 (governed range 0.85–1.15)"],
          ["Top 5% queue", "precision 35.31% · lift 2.31×"],
        ],
        source: ["simulator/src/inforsight_simulator/calibration.py"],
      },
    },
    {
      id: "l-bundle",
      number: "H",
      title: "Model bundle",
      tech: `sha256 ${BUNDLE_SHA256.slice(0, 8)}…`,
      icon: Package,
      tone: "model",
      x: offX(7),
      y: OFF_Y,
      w: 140,
      h: 116,
      chips: ["v1.0.0"],
      detail: {
        summary:
          "One JSON artifact with the coefficients, calibrator, preprocessing, risk tiers, review queues, authority boundaries, explainer reference and locked runtime environment. Its bytes are copied into the inference image and verified at startup.",
        facts: [
          ["Bundle ID", BUNDLE_ID],
          ["Created", "2026-09-04T19:30:00Z"],
          ["Base rate", "p = 0.1328 over 8,782 background rows"],
          ["Risk tiers", "< 10% · 10–25% · 25–50% · ≥ 50%"],
        ],
        source: ["docs/experiments/phase-02-10-model-bundle.json", "MODEL_CARD.md"],
      },
    },
    {
      id: "o-source",
      number: "01",
      title: "Source history",
      tech: "policy · payment · safety events",
      icon: FileText,
      tone: "python",
      x: colX(0),
      y: rowY(0),
      w: ONLINE_W,
      h: 112,
      chips: ["trigger + later recovery"],
      stages: ["submission"],
      live: "source",
      detail: {
        summary:
          "A fictional policy issued 365 days before the cutoff, five on-time monthly payments, the submitted late payment, a later recovery after the cutoff, and safety facts. Java persists it in the run and the outbox.",
        source: ["demo_runtime/app.py (scenario)"],
      },
    },
    {
      id: "o-projection",
      number: "02",
      title: "Point-in-time projection",
      tech: "cutoff 2026-09-25T12:00Z",
      icon: Layers3,
      tone: "python",
      x: colX(1),
      y: rowY(0),
      w: ONLINE_W,
      h: 112,
      chips: ["later events excluded"],
      stages: ["snapshot"],
      live: "projection",
      detail: {
        summary:
          "Rebuilds domain and payment snapshots from two source profiles that must agree, keeps only events visible at the cutoff, and records every excluded event ID.",
        source: ["demo_runtime/app.py (project)", "simulator/src/inforsight_simulator/domain_snapshot.py"],
      },
    },
    {
      id: "o-snapshot",
      number: "03",
      title: "Snapshot",
      tech: "snapshot_id = SHA-256(canonical JSON)",
      icon: Hash,
      tone: "python",
      x: colX(2),
      y: rowY(0),
      w: ONLINE_W,
      h: 112,
      chips: ["content-addressed"],
      stages: ["snapshot"],
      live: "snapshot",
      detail: {
        summary:
          "The frozen facts this run knew: status, tenure, premium, days past due, grace period, safety facts and provenance. Downstream services recompute and check its identity.",
        source: ["demo_runtime/app.py (project, validate_snapshot)"],
      },
    },
    {
      id: "o-features",
      number: "04",
      title: "Raw V6 features",
      tech: "17 features with lineage",
      icon: SlidersHorizontal,
      tone: "python",
      x: colX(3),
      y: rowY(0),
      w: ONLINE_W,
      h: 112,
      chips: ["13 numeric · 4 categorical"],
      stages: ["snapshot"],
      live: "features",
      detail: {
        summary:
          "The model input reconstructed from visible payment events, with lineage back to source event IDs. It is sent to the inference runtime unchanged.",
        source: ["simulator/src/inforsight_simulator/v6_corpus.py (reconstruct_v6_features)"],
      },
    },
    {
      id: "o-score",
      number: "05",
      title: "Risk score",
      tech: "released bundle · calibrated",
      icon: Activity,
      tone: "model",
      x: colX(3),
      y: rowY(1),
      w: ONLINE_W,
      h: 112,
      chips: ["probability · tier · drivers"],
      stages: ["score"],
      live: "score",
      detail: {
        summary:
          "The calibrated 90-day lapse-or-surrender probability, its tier and log-odds attributions. Attributions describe statistical association, not causes, and the score carries no authority.",
        source: ["serving/app.py"],
      },
    },
    {
      id: "o-rules",
      number: "06",
      title: "Eligibility",
      tech: "java-eligibility/1.0.0",
      icon: ShieldCheck,
      tone: "java",
      x: colX(2),
      y: rowY(1),
      w: ONLINE_W,
      h: 112,
      chips: ["5 actions · fail-closed"],
      stages: ["rules"],
      live: "rules",
      detail: {
        summary:
          "Five actions evaluated fail-closed: missing safety evidence, a legal hold, an active claim or a dispute freeze blocks all but abstain; then policy status, channel opt-outs and do-not-call, cooling-off, grace-period and tenure rules.",
        facts: [["Actions", "courtesy_reminder · payment_method_remediation · grace_period_consultation · specialist_phone_outreach · abstain"]],
        source: [`${JAVA}/rules/EligibilityEngine.java`, `${JAVA}/domain/ActionDefinition.java`],
      },
    },
    {
      id: "o-valuation",
      number: "07",
      title: "Valuation",
      tech: "economics contract v1.0.0",
      icon: Calculator,
      tone: "python",
      x: colX(1),
      y: rowY(1),
      w: ONLINE_W,
      h: 112,
      chips: ["expected, not realized"],
      stages: ["allocation"],
      live: "valuation",
      detail: {
        summary:
          "Net expected value = modeled effect × annual premium − direct cost, in USD micros with half-even rounding. It means expected one-year premium preserved, not profit, revenue or realized savings.",
        source: ["demo_runtime/app.py (value)", "data-contracts/rh/economics/v1/economics-resource-contract.json"],
      },
    },
    {
      id: "o-allocation",
      number: "08",
      title: "Allocation",
      tech: "multiple-choice knapsack",
      icon: Scale,
      tone: "java",
      x: colX(0),
      y: rowY(1),
      w: ONLINE_W,
      h: 112,
      chips: ["$30 · 1,800 s · ≤ 1 action"],
      stages: ["allocation"],
      live: "allocation",
      detail: {
        summary:
          "Dynamic programming over money and time states selects at most one eligible action for the policy within $30 and 1,800 personnel seconds, maximizing modeled net value with deterministic tie-breaks.",
        source: [`${JAVA}/allocation/PortfolioAllocator.java`],
      },
    },
    {
      id: "o-case",
      number: "09",
      title: "Case record",
      tech: "4 evidence digests",
      icon: Database,
      tone: "data",
      x: colX(0),
      y: rowY(2),
      w: ONLINE_W,
      h: 112,
      chips: ["starts AWAITING_REVIEW, v0"],
      stages: ["case"],
      live: "case",
      detail: {
        summary:
          "demo_case binds the snapshot, score, rules and allocation by SHA-256 digest, along with the bundle digest and the recommended action. Authority and external execution are false.",
        source: [`${JAVA}/demo/DemoJourneyWorker.java (case stage)`],
      },
    },
    {
      id: "o-agent",
      number: "10",
      title: "Agent draft",
      tech: "inforsight-bounded-agent/1.0.0",
      icon: Sparkles,
      tone: "python",
      x: colX(1),
      y: rowY(2),
      w: ONLINE_W,
      h: 112,
      chips: ["cited draft or abstention"],
      stages: ["agent"],
      live: "agent",
      detail: {
        summary:
          "Deterministic evidence, procedure and planner checks. A draft must match the allocated action, cite fictional-local-review@1.0.0 and use only snapshot evidence; otherwise the agent abstains with reason codes.",
        source: ["agents/workflow.py", "demo_runtime/app.py (draft)"],
      },
    },
    {
      id: "o-decision",
      number: "11",
      title: "Human decision",
      tech: "case_version + 1",
      icon: FileCheck2,
      tone: "human",
      x: colX(2),
      y: rowY(2),
      w: ONLINE_W,
      h: 112,
      chips: ["approve · reject · request info"],
      stages: ["decision"],
      live: "decision",
      detail: {
        summary:
          "Your decision, rationale, reviewer label and expected case version. Idempotent by key; a stale version conflicts; an abstention cannot be approved.",
        source: [`${JAVA}/demo/DemoStore.java (decide)`],
      },
    },
    {
      id: "o-journal",
      number: "12",
      title: "Journal and verification",
      tech: "SHA-256 chain + checkpoint",
      icon: Link2,
      tone: "data",
      x: colX(3),
      y: rowY(2),
      w: ONLINE_W,
      h: 112,
      chips: ["21 rows per completed run"],
      stages: ["audit"],
      live: "journal",
      detail: {
        summary:
          "Every stage transition is an append-only journal entry hashed onto its parent. Verification recomputes the chain and checks the displayed evidence against it.",
        source: [`${JAVA}/demo/DemoJournalVerifier.java`, `${JAVA}/demo/DemoStore.java (verify)`],
      },
    },
  ],
  edges: [
    ...["l-sim", "l-events", "l-observations", "l-splits", "l-features", "l-model", "l-calibration"].map(
      (from, index, all): ArchEdge => ({
        id: `e-${from}`,
        from,
        to: all[index + 1] ?? "l-bundle",
        fromSide: "right",
        toSide: "left",
        kind: "data",
        detail: { summary: "Offline lineage: each step consumes only the previous step's versioned output." },
      }),
    ),
    {
      id: "e-bundle",
      from: "l-bundle",
      to: "o-score",
      fromSide: "bottom",
      toSide: "right",
      via: [
        [1146, 240],
        [1222, 240],
        [1222, rowY(1) + 56],
      ],
      kind: "control",
      label: "pinned bundle",
      labelAt: [1184, 240],
      stages: ["score"],
      detail: {
        summary:
          "The inference image copies the bundle file and requires its SHA-256, ID and version at startup (INFORSIGHT_REQUIRE_TRUSTED_BUNDLE=true). Java pins the same identity on every response.",
        facts: [
          ["Bundle", `${BUNDLE_ID} v1.0.0`],
          ["SHA-256", BUNDLE_SHA256],
        ],
      },
    },
    ...(
      [
        ["o-source", "o-projection", "right", "left", "submission"],
        ["o-projection", "o-snapshot", "right", "left", "snapshot"],
        ["o-snapshot", "o-features", "right", "left", "snapshot"],
        ["o-features", "o-score", "bottom", "top", "score"],
        ["o-score", "o-rules", "left", "right", "rules"],
        ["o-rules", "o-valuation", "left", "right", "allocation"],
        ["o-valuation", "o-allocation", "left", "right", "allocation"],
        ["o-allocation", "o-case", "bottom", "top", "case"],
        ["o-case", "o-agent", "right", "left", "agent"],
        ["o-agent", "o-decision", "right", "left", "decision"],
        ["o-decision", "o-journal", "right", "left", "audit"],
      ] as const
    ).map(
      ([from, to, fromSide, toSide, stage]): ArchEdge => ({
        id: `e-${from}`,
        from,
        to,
        fromSide,
        toSide,
        kind: "data",
        stages: [stage],
        detail: { summary: "Per-run lineage: the next artifact is computed from this persisted artifact." },
      }),
    ),
  ],
  steps: [
    {
      title: "Simulate and record",
      text: "The v6 simulator generates fictional policy histories as immutable, dual-time event streams that match versioned JSON Schema contracts.",
      anchor: "l-sim",
      nodes: ["l-sim", "l-events"],
      edges: ["e-l-sim"],
    },
    {
      title: "Observe without leakage",
      text: "Observation records see only events visible at each cutoff, carry a 90-day lapse-or-surrender label, and are split by policy and time.",
      anchor: "l-observations",
      nodes: ["l-observations", "l-splits"],
      edges: ["e-l-events", "e-l-observations"],
    },
    {
      title: "Learn and calibrate",
      text: "Seventeen features become 28 model columns; an L2 logistic regression is fitted and Platt-calibrated so probabilities match observed rates.",
      anchor: "l-features",
      nodes: ["l-features", "l-model", "l-calibration"],
      edges: ["e-l-splits", "e-l-features", "e-l-model"],
    },
    {
      title: "Release one pinned bundle",
      text: "The bundle file is the release. Its SHA-256 is pinned in the inference image and in Java, so a different model cannot score silently.",
      anchor: "l-bundle",
      nodes: ["l-bundle", "o-score"],
      edges: ["e-l-calibration", "e-bundle"],
    },
    {
      title: "Freeze what was knowable",
      text: "Each run's fictional history is projected at its cutoff into a content-addressed snapshot and 17 raw features; later events are listed as excluded.",
      anchor: "o-source",
      nodes: ["o-source", "o-projection", "o-snapshot", "o-features"],
      edges: ["e-o-source", "e-o-projection", "e-o-snapshot"],
      stages: ["submission", "snapshot"],
    },
    {
      title: "Score, constrain and value",
      text: "The pinned model scores the features; deterministic rules decide what is allowed; modeled value and capacity decide what is affordable.",
      anchor: "o-score",
      nodes: ["o-score", "o-rules", "o-valuation", "o-allocation"],
      edges: ["e-o-features", "e-o-score", "e-o-rules", "e-o-valuation"],
      stages: ["score", "rules", "allocation"],
    },
    {
      title: "Bind, draft, decide and verify",
      text: "The case binds four evidence digests, the agent drafts or abstains, you decide, and the journal proves what was recorded in what order.",
      anchor: "o-case",
      nodes: ["o-case", "o-agent", "o-decision", "o-journal"],
      edges: ["e-o-allocation", "e-o-case", "e-o-agent", "e-o-decision"],
      stages: ["case", "agent", "decision", "audit"],
    },
  ],
};

// ---------------------------------------------------------------------------
// 4. Lifecycle: run status, stage status and case state machines.
// ---------------------------------------------------------------------------
const lifecycleLens: GraphLens = {
  kind: "graph",
  ...lensMeta("lifecycle"),
  title: "Every state a run, stage, and case can reach",
  summary:
    "The persisted state machines behind the status badges: what moves a run forward, what fails it, what retries it, and what expires it.",
  reading:
    "Boxes are persisted states; arrows are the only transitions the code allows, labeled with their trigger. Bound to a run, the current state is highlighted.",
  width: 1240,
  height: 760,
  stepsTitle: "Transitions",
  focus: {
    submission: "lc-waiting",
    publication: "lc-waiting",
    ingestion: "lc-processing",
    snapshot: "lc-processing",
    score: "lc-processing",
    rules: "lc-processing",
    allocation: "lc-processing",
    case: "lc-processing",
    agent: "lc-processing",
    decision: "lc-awaiting",
    audit: "lc-completed",
  },
  groups: [
    { id: "g-run", label: "Run status", caption: "demo_run.status · one per correlation ID", x: 12, y: 30, w: 1216, h: 440, variant: "zone" },
    { id: "g-stage", label: "Stage status", caption: "11 per run · stages[].status", x: 12, y: 494, w: 742, h: 254, variant: "network" },
    { id: "g-case", label: "Case state", caption: "demo_case.state · versioned", x: 774, y: 494, w: 454, h: 254, variant: "private" },
  ],
  nodes: [
    {
      id: "lc-start",
      title: "POST /runs",
      tech: "202 Accepted",
      icon: Send,
      tone: "client",
      x: 16,
      y: 124,
      w: 132,
      h: 72,
      detail: {
        summary:
          "A valid, quota-admitted submission creates the run, its outbox row and journal entry 1 in one transaction. A repeated Idempotency-Key with the same body replays the existing run instead.",
      },
    },
    {
      id: "lc-waiting",
      mono: true,
      title: "WAITING",
      tech: "accepted · awaiting broker delivery",
      icon: Hourglass,
      tone: "state",
      x: 196,
      y: 98,
      w: 170,
      h: 124,
      states: ["WAITING"],
      live: "runStatus",
      detail: {
        summary:
          "The submission is durable, but processing has not started. The worker publishes the outbox envelope to Kafka; the status changes only when the delivered event is recorded in the inbox.",
        facts: [["Stages", "submission completed · publication processing or waiting"]],
      },
    },
    {
      id: "lc-processing",
      mono: true,
      title: "PROCESSING",
      tech: "inbox recorded · worker running",
      icon: Activity,
      tone: "state",
      x: 480,
      y: 98,
      w: 170,
      h: 124,
      states: ["PROCESSING"],
      live: "runStatus",
      detail: {
        summary:
          "The event has been delivered and recorded. The worker runs snapshot, score, rules, allocation, case and agent in order, skipping any stage already committed, so a restart resumes where it stopped.",
        facts: [["Resumable", "resumable() lists PROCESSING runs with an inbox row, 10 at a time"]],
      },
    },
    {
      id: "lc-awaiting",
      mono: true,
      title: "AWAITING_REVIEW",
      tech: "draft or abstention persisted",
      icon: UserRound,
      tone: "human",
      x: 764,
      y: 98,
      w: 170,
      h: 124,
      states: ["AWAITING_REVIEW"],
      live: "runStatus",
      detail: {
        summary:
          "The agent stage committed a draft or an abstention. Nothing advances until a person records a decision. Approval is accepted only for an allocated, non-abstained draft.",
      },
    },
    {
      id: "lc-completed",
      mono: true,
      title: "COMPLETED",
      tech: "decision + verified audit",
      icon: CheckCircle2,
      tone: "state",
      x: 1048,
      y: 98,
      w: 170,
      h: 124,
      states: ["COMPLETED"],
      live: "runStatus",
      detail: {
        summary:
          "The decision and a successful audit verification committed together. Polling stops. Evidence stays readable until retention removes the whole run.",
      },
    },
    {
      id: "lc-failed",
      mono: true,
      title: "FAILED",
      tech: "stage failed · later stages blocked",
      icon: CircleX,
      tone: "security",
      x: 480,
      y: 300,
      w: 170,
      h: 112,
      states: ["FAILED"],
      live: "runStatus",
      detail: {
        summary:
          "A component did not produce a verified output. The failing stage records a retryable error code, every later waiting stage becomes blocked, and completed evidence is kept.",
        facts: [["Error codes", "e.g. COMPONENT_UNAVAILABLE, DEPENDENCY_HTTP_503, AGENT_BINDING_OR_AUTHORITY_MISMATCH"]],
      },
    },
    {
      id: "lc-expired",
      mono: true,
      title: "EXPIRED",
      tech: "abandoned review · public preview",
      icon: CalendarClock,
      tone: "ops",
      x: 764,
      y: 300,
      w: 170,
      h: 112,
      states: ["EXPIRED"],
      live: "runStatus",
      detail: {
        summary:
          "In the public preview, a review that is more than 48 hours old and unvisited for 24 hours expires. Decision and audit become blocked with RUN_EXPIRED; this is never a human decision.",
      },
    },
    {
      id: "lc-purged",
      title: "Purged · 410",
      tech: "verified deletion + receipt",
      icon: Trash2,
      tone: "ops",
      x: 1048,
      y: 300,
      w: 170,
      h: 112,
      detail: {
        summary:
          "Public retention deletes a terminal run 24 hours after its last update, but only after its journal verifies. A receipt with the verified head hash is kept for 7 days and later requests get 410 Gone.",
        facts: [["Order", "decision → case → checkpoint → journal → inbox → outbox → run"]],
      },
    },
    {
      id: "st-waiting",
      mono: true,
      title: "waiting",
      tech: "no record yet",
      icon: Circle,
      tone: "state",
      x: 32,
      y: 590,
      w: 132,
      h: 64,
      live: "stageStatus",
      detail: { summary: "The stage has no started record. The interface never marks it complete on its own." },
    },
    {
      id: "st-processing",
      mono: true,
      title: "processing",
      tech: "started_at recorded",
      icon: Activity,
      tone: "state",
      x: 214,
      y: 590,
      w: 140,
      h: 64,
      live: "stageStatus",
      detail: { summary: "The worker committed started_at and incremented the attempt counter before calling the component." },
    },
    {
      id: "st-completed",
      mono: true,
      title: "completed",
      tech: "evidence + output digest",
      icon: Check,
      tone: "state",
      x: 412,
      y: 540,
      w: 150,
      h: 56,
      live: "stageStatus",
      detail: { summary: "Evidence, the sha256 output reference and the duration are committed with a journal entry." },
    },
    {
      id: "st-abstained",
      mono: true,
      title: "abstained",
      tech: "agent stage only",
      icon: Pause,
      tone: "state",
      x: 412,
      y: 606,
      w: 150,
      h: 56,
      live: "stageStatus",
      detail: { summary: "A recorded outcome, not a failure: the bounded agent declined to draft and listed its reasons." },
    },
    {
      id: "st-failed",
      mono: true,
      title: "failed",
      tech: "retryable error code",
      icon: X,
      tone: "security",
      x: 412,
      y: 672,
      w: 150,
      h: 56,
      live: "stageStatus",
      detail: { summary: "The stage error is recorded with retryable: true; the run becomes FAILED." },
    },
    {
      id: "st-blocked",
      mono: true,
      title: "blocked",
      tech: "after a failure or expiry",
      icon: LockKeyhole,
      tone: "ops",
      x: 602,
      y: 672,
      w: 138,
      h: 56,
      live: "stageStatus",
      detail: { summary: "Later stages wait behind a failure. Retry returns failed and blocked stages to waiting." },
    },
    {
      id: "cs-awaiting",
      mono: true,
      title: "AWAITING_REVIEW",
      tech: "case_version 0",
      icon: Hourglass,
      tone: "data",
      x: 796,
      y: 596,
      w: 170,
      h: 70,
      live: "caseState",
      states: ["AWAITING_REVIEW"],
      detail: { summary: "Inserted by the case stage with four evidence digests." },
    },
    {
      id: "cs-approved",
      mono: true,
      title: "HUMAN_APPROVED",
      tech: "case_version 1",
      icon: FileCheck2,
      tone: "human",
      x: 1024,
      y: 538,
      w: 186,
      h: 56,
      live: "caseState",
      states: ["HUMAN_APPROVED"],
      detail: { summary: "Approval of an allocated draft. It still carries authorized_to_act: false; nothing is executed." },
    },
    {
      id: "cs-rejected",
      mono: true,
      title: "REJECTED",
      tech: "case_version 1",
      icon: X,
      tone: "human",
      x: 1024,
      y: 603,
      w: 186,
      h: 56,
      live: "caseState",
      states: ["REJECTED"],
      detail: { summary: "The reviewer declined the recommendation or the abstention, with a rationale." },
    },
    {
      id: "cs-info",
      mono: true,
      title: "MORE_INFORMATION_\u200bREQUESTED",
      tech: "case_version 1",
      icon: FileText,
      tone: "human",
      x: 1024,
      y: 670,
      w: 186,
      h: 56,
      live: "caseState",
      states: ["MORE_INFORMATION_REQUESTED"],
      detail: { summary: "A recorded outcome. Collecting new evidence and re-review are not implemented." },
    },
  ],
  edges: [
    { id: "t-accept", from: "lc-start", to: "lc-waiting", fromSide: "right", toSide: "left", kind: "request", stages: ["submission"], detail: { summary: "Run, outbox and submission.completed are written in one transaction." } },
    { id: "t-deliver", from: "lc-waiting", to: "lc-processing", fromSide: "right", toSide: "left", kind: "event", label: "inbox receipt", stages: ["ingestion"], detail: { summary: "DemoStore.ingest records the delivered envelope in demo_inbox and sets PROCESSING." } },
    { id: "t-draft", from: "lc-processing", to: "lc-awaiting", fromSide: "right", toSide: "left", kind: "request", label: "agent done", stages: ["agent"], detail: { summary: "The agent stage finishing (completed or abstained) sets AWAITING_REVIEW." } },
    { id: "t-decide", from: "lc-awaiting", to: "lc-completed", fromSide: "right", toSide: "left", kind: "control", label: "decision", stages: ["decision", "audit"], detail: { summary: "DemoStore.decide records the decision and the verified audit, then sets COMPLETED." } },
    { id: "t-fail-publish", from: "lc-waiting", to: "lc-failed", fromSide: "bottom", toSide: "left", fromOffset: -44, toOffset: -20, kind: "data", label: "publish failed", stages: ["publication"], detail: { summary: "A send failure or timeout fails publication and the run. The outbox row is not sent again until an explicit retry, and at most 3 attempts are made between retries." } },
    { id: "t-fail", from: "lc-processing", to: "lc-failed", fromSide: "bottom", toSide: "top", fromOffset: -48, toOffset: -48, kind: "data", label: "stage failed", stages: ["snapshot", "score", "rules", "allocation", "case", "agent"], detail: { summary: "Any processing stage failure: dependency errors, identity mismatches or authority violations." } },
    { id: "t-retry", from: "lc-failed", to: "lc-processing", fromSide: "top", toSide: "bottom", fromOffset: 48, toOffset: 48, kind: "control", label: "retry", detail: { summary: "POST /runs/{id}/retry when the inbox row exists: failed and blocked stages return to waiting and the worker resumes." } },
    { id: "t-retry-waiting", from: "lc-failed", to: "lc-waiting", fromSide: "bottom", toSide: "bottom", fromOffset: -40, toOffset: 44, via: [[525, 446], [325, 446]], kind: "control", label: "retry before delivery", labelAt: [425, 446], detail: { summary: "POST /runs/{id}/retry when nothing was delivered yet: the outbox attempt counter resets and the run returns to WAITING." } },
    { id: "t-expire", from: "lc-awaiting", to: "lc-expired", fromSide: "bottom", toSide: "top", kind: "control", label: "48 h old · 24 h idle", detail: { summary: "DemoPublicAccess.cleanup runs every 60 s and expires abandoned reviews (public preview only)." } },
    { id: "t-purge-completed", from: "lc-completed", to: "lc-purged", fromSide: "bottom", toSide: "top", kind: "control", label: "24 h idle", detail: { summary: "Terminal runs are verified, receipted and deleted 24 hours after their last update (public preview only)." } },
    { id: "t-purge-expired", from: "lc-expired", to: "lc-purged", fromSide: "right", toSide: "left", kind: "control", label: "24 h idle", detail: { summary: "Expired runs follow the same verified retention path." } },
    { id: "t-purge-failed", from: "lc-failed", to: "lc-purged", fromSide: "bottom", toSide: "bottom", fromOffset: 60, via: [[625, 456], [1133, 456]], kind: "control", label: "24 h idle", detail: { summary: "Failed runs that are not retried are also removed after verification." } },
    { id: "s-start", from: "st-waiting", to: "st-processing", fromSide: "right", toSide: "left", kind: "request", label: "start", detail: { summary: "startInRun: status processing, attempt + 1, started_at, journal entry." } },
    { id: "s-complete", from: "st-processing", to: "st-completed", fromSide: "right", toSide: "left", toOffset: 0, via: [[384, 622], [384, 568]], kind: "request", detail: { summary: "finishInRun with status completed." } },
    { id: "s-abstain", from: "st-processing", to: "st-abstained", fromSide: "right", toSide: "left", kind: "request", detail: { summary: "Only the agent stage can finish as abstained." } },
    { id: "s-fail", from: "st-processing", to: "st-failed", fromSide: "right", toSide: "left", via: [[384, 622], [384, 700]], kind: "data", detail: { summary: "fail(): the error is recorded and later waiting stages become blocked." } },
    { id: "s-block", from: "st-failed", to: "st-blocked", fromSide: "right", toSide: "left", kind: "data", detail: { summary: "Every later stage still waiting is set to blocked." } },
    { id: "s-retry", from: "st-blocked", to: "st-waiting", fromSide: "bottom", toSide: "bottom", via: [[671, 740], [98, 740]], kind: "control", label: "POST /retry", labelAt: [300, 740], detail: { summary: "Retry resets failed and blocked stages to waiting; completed evidence and earlier journal entries remain." } },
    { id: "c-approve", from: "cs-awaiting", to: "cs-approved", fromSide: "right", toSide: "left", kind: "control", detail: { summary: "decision = APPROVED" } },
    { id: "c-reject", from: "cs-awaiting", to: "cs-rejected", fromSide: "right", toSide: "left", kind: "control", detail: { summary: "decision = REJECTED" } },
    { id: "c-info", from: "cs-awaiting", to: "cs-info", fromSide: "right", toSide: "left", kind: "control", detail: { summary: "decision = REQUEST_MORE_INFORMATION" } },
  ],
  steps: [
    {
      title: "Accepted",
      text: "A valid submission commits the run as WAITING with its outbox row. Nothing is processed until Kafka delivers the event back.",
      anchor: "t-accept",
      nodes: ["lc-start", "lc-waiting"],
      edges: ["t-accept"],
      stages: ["submission", "publication"],
    },
    {
      title: "Delivered and processing",
      text: "The inbox receipt moves the run to PROCESSING. Each stage goes waiting → processing → completed, journaled at both transitions.",
      anchor: "t-deliver",
      nodes: ["lc-processing", "st-waiting", "st-processing", "st-completed"],
      edges: ["t-deliver", "s-start", "s-complete"],
      stages: ["ingestion", "snapshot", "score", "rules", "allocation", "case"],
    },
    {
      title: "Ready for a person",
      text: "When the agent stage completes or abstains, the run waits in AWAITING_REVIEW. Only a human decision moves it forward.",
      anchor: "t-draft",
      nodes: ["lc-awaiting", "st-abstained", "cs-awaiting"],
      edges: ["t-draft", "s-abstain"],
      stages: ["agent"],
    },
    {
      title: "Decided and verified",
      text: "The decision increments the case version and sets the case state. The audit verification commits in the same transaction, so COMPLETED always means verified.",
      anchor: "t-decide",
      nodes: ["lc-completed", "cs-approved", "cs-rejected", "cs-info"],
      edges: ["t-decide", "c-approve", "c-reject", "c-info"],
      stages: ["decision", "audit"],
    },
    {
      title: "Failure and retry",
      text: "A failing component marks its stage failed and blocks later ones. POST /retry resumes the same run; completed evidence is never recomputed or rewritten.",
      anchor: "t-fail",
      nodes: ["lc-failed", "st-failed", "st-blocked"],
      edges: ["t-fail-publish", "t-fail", "t-retry", "t-retry-waiting", "s-fail", "s-block", "s-retry"],
    },
    {
      title: "Expiry and retention",
      text: "In the public preview, abandoned reviews expire and terminal runs are deleted after 24 idle hours, only after their journal verifies and a receipt is written.",
      anchor: "t-expire",
      nodes: ["lc-expired", "lc-purged"],
      edges: ["t-expire", "t-purge-completed", "t-purge-expired", "t-purge-failed"],
    },
  ],
};

// ---------------------------------------------------------------------------
// 5. Security: layered controls a request passes, and what stays isolated.
// ---------------------------------------------------------------------------
const securityLens: GraphLens = {
  kind: "graph",
  ...lensMeta("security"),
  title: "Defense in depth, from the internet to the journal",
  summary:
    "Each control a request must pass, in order, and the isolation around them. No single layer is trusted alone.",
  reading:
    "Read the top row left to right as a request travels inward. The lower row protects evidence and authority after a request is accepted.",
  width: 1240,
  height: 720,
  deployable: true,
  stepsTitle: "Controls",
  focus: { submission: "sec-contract", decision: "sec-authority", audit: "sec-integrity" },
  groups: [
    { id: "g-path", label: "Request path", caption: "outside → inside", x: 12, y: 30, w: 1216, h: 336, variant: "network" },
    { id: "g-core", label: "After acceptance", caption: "authority, evidence and isolation", x: 12, y: 388, w: 1216, h: 316, variant: "private" },
  ],
  nodes: [
    {
      id: "sec-edge",
      number: "1",
      title: "Edge and tunnel",
      tech: "Cloudflare · outbound-only",
      icon: Globe,
      tone: "edge",
      x: 32,
      y: 82,
      w: 270,
      h: 258,
      bullets: [
        "TLS terminated at Cloudflare",
        "Tunnel dialed out from the Mac; no inbound port",
        "Only the gateway hostname is routed",
        "Dashboard and backend ports never routed",
      ],
      deployments: ["public"],
      live: "edge",
      detail: {
        summary:
          "The internet only ever reaches Cloudflare. The Mac opens connections outward, so there is no listening port to attack, and only one hostname maps to one loopback port.",
        source: ["docs/showcase/public-preview.md", "scripts/public_site.sh"],
      },
    },
    {
      id: "sec-edge",
      number: "1",
      title: "Loopback only",
      tech: "127.0.0.1 port bindings",
      icon: Laptop,
      tone: "edge",
      x: 32,
      y: 82,
      w: 270,
      h: 258,
      bullets: [
        "Every published port binds to 127.0.0.1",
        "No tunnel and no remote access",
        "Development credentials stay on this machine",
        "demo-runtime publishes no port at all",
      ],
      deployments: ["local"],
      live: "edge",
      detail: {
        summary:
          "The local stack is reachable only from this computer. The development database password in Compose is acceptable only because nothing is exposed.",
        source: ["infra/docker-compose.yml"],
      },
    },
    {
      id: "sec-gateway",
      number: "2",
      title: "Gateway allowlist",
      tech: "nginx · before any Java code",
      icon: Server,
      tone: "gateway",
      x: 330,
      y: 82,
      w: 270,
      h: 258,
      chips: ["30 r/s · burst 60"],
      bullets: [
        "Exact demo routes only; other /api/ → 404",
        "≤ 32 KB bodies · 10 s client timeouts",
        "CSP 'self' · frame-ancestors 'none'",
        "no-store on every API response",
        "Client X-Forwarded-* headers overwritten",
      ],
      detail: nginxBase.detail,
    },
    {
      id: "sec-session",
      number: "3",
      title: "Signed visitor session",
      tech: "DemoSessionFilter · HMAC-SHA256",
      icon: Cookie,
      tone: "java",
      x: 628,
      y: 82,
      w: 270,
      h: 258,
      bullets: [
        "__Host- cookie · HttpOnly · Secure · SameSite=Strict",
        "Signed token plus a database session row",
        "Mutations need CSRF and Origin = Host",
        "Durable per-session and global quotas",
        "A copied correlation ID grants nothing",
      ],
      deployments: ["public"],
      live: "session",
      detail: {
        summary:
          "Public mode authenticates an anonymous visitor, not a person. A session cookie owns that visitor's runs; a copied correlation ID grants nothing.",
        facts: [
          ["Token", "session_id.expiry.HMAC-SHA256(secret, 'cookie:'+payload)"],
          ["CSRF", "HMAC(secret, 'csrf:'+session_id) in X-Demo-CSRF"],
          ["Paths rejected", "Any %, ., ; or // in the path, and unknown routes"],
          ["Secret", "≥ 32 bytes, read from a mounted file"],
        ],
        sections: [
          {
            title: "Quotas (PostgreSQL demo_quota)",
            items: [
              "240 requests/min per session and 2,400 overall, plus per-operation limits.",
              "Submissions, polls, retries and decisions each have per-session and global windows.",
              "Concurrent and retained run capacity is checked inside the submission transaction.",
            ],
          },
        ],
        source: [`${JAVA}/demo/DemoSessionFilter.java`, `${JAVA}/demo/DemoPublicAccess.java`],
      },
    },
    {
      id: "sec-session",
      number: "3",
      title: "Visitor filter disabled",
      tech: "loopback demo mode",
      icon: Cookie,
      tone: "java",
      x: 628,
      y: 82,
      w: 270,
      h: 258,
      bullets: [
        "INFORSIGHT_DEMO_PUBLIC_ENABLED is false",
        "No cookie, CSRF or quota enforcement",
        "Loopback binding is the access control",
        "Validation and authority rules still apply",
      ],
      deployments: ["local"],
      live: "session",
      detail: {
        summary:
          "Locally there is one trusted operator, so the public visitor filter is not installed. Everything after it, including the request contract and the authority boundary, is identical.",
        source: [`${JAVA}/demo/DemoSessionFilter.java (shouldNotFilter)`],
      },
    },
    {
      id: "sec-contract",
      number: "4",
      title: "Request contract",
      tech: "DemoJourneyController · DemoStore",
      icon: Filter,
      tone: "java",
      x: 926,
      y: 82,
      w: 282,
      h: 258,
      bullets: [
        "Exact JSON fields; unknown fields → 400",
        "Premium 1,000–100,000 ¢ · delay 1–45 days",
        "Idempotency-Key ≤ 128 chars, digest-checked",
        "Other visitors' runs → 404; purged → 410",
        "Public capacity: 2 processing · 12 retained runs",
      ],
      live: "contract",
      detail: {
        summary:
          "Only allowlisted, bounded inputs reach the services, and repeated requests are idempotent rather than duplicated.",
        sections: [
          {
            title: "Idempotency",
            items: [
              "Public keys are scoped by HMAC to the session, so two visitors cannot collide.",
              "The same key with a different body is a 409 conflict.",
              "Decisions have their own idempotency table and expected case version.",
            ],
          },
        ],
        source: [`${JAVA}/demo/DemoJourneyController.java`, `${JAVA}/demo/DemoStore.java`],
      },
    },
    {
      id: "sec-authority",
      number: "5",
      title: "No action authority",
      tech: "ADR 0002 · enforced at every hop",
      icon: LockKeyhole,
      tone: "security",
      x: 32,
      y: 438,
      w: 270,
      h: 248,
      bullets: [
        "Model, rules and agent return authorized_to_act: false",
        "A dependency claiming authority is rejected",
        "Approval cannot authorize an abstention",
        "External execution disabled in every service",
      ],
      live: "authority",
      detail: {
        summary:
          "Risk perception, eligibility, drafting and human review are separate, and no layer can contact a customer or change a policy. Even an approved case only records a fictional decision.",
        facts: [
          ["Flags", "INFORSIGHT_EXTERNAL_EXECUTION_ENABLED=false · INFORSIGHT_AUTHORIZED_TO_ACT=false"],
          ["Decision record", "human_authority: true · authorized_to_act: false"],
        ],
        source: ["docs/adr/0002-separate-risk-from-action-eligibility.md", `${JAVA}/demo/DemoRuntimeClient.java`],
      },
    },
    {
      id: "sec-integrity",
      number: "6",
      title: "Evidence integrity",
      tech: "transactions · append-only · SHA-256",
      icon: Fingerprint,
      tone: "data",
      x: 330,
      y: 438,
      w: 270,
      h: 248,
      bullets: [
        "One transaction per stage under a row lock",
        "Trigger blocks journal UPDATE and DELETE",
        "Chain verified before a decision is stored",
        "Displayed evidence must equal the journal",
        "Retention deletes only verified runs",
      ],
      live: "integrity",
      detail: {
        summary:
          "Evidence is written once, linked by hash, and checked against what you see. The audit chain lens shows each verification step.",
        sections: [
          {
            title: "Scope",
            items: [
              "The checkpoint shares PostgreSQL's trust domain; it is not externally anchored.",
              "Retention deletes a whole run only after it verifies, inside the receipt transaction.",
            ],
          },
        ],
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`, `${JAVA}/demo/DemoStore.java`],
      },
    },
    {
      id: "sec-isolation",
      number: "7",
      title: "Container and host isolation",
      tech: "Compose · networks · secrets",
      icon: Container,
      tone: "ops",
      x: 628,
      y: 438,
      w: 580,
      h: 248,
      bullets: [
        "Backend network is internal: no internet egress",
        "Only the gateway publishes a port, on loopback",
        "Java and Python run as non-root · no-new-privileges",
        "Secrets: 0400 files read via configtree or _FILE",
        "Dashboard: read-only root FS, all capabilities dropped",
        "Memory caps · bounded JSON logs · restart unless-stopped",
      ],
      deployments: ["public"],
      detail: {
        summary:
          "Even a compromised component has little reach: backend containers cannot call the internet, secrets are files rather than environment variables, and the analytics service sees only page-view logs.",
        facts: [
          ["Memory caps", "Kafka 1 GB · Java 1 GB · PostgreSQL 512 MB · Python 384 MB each · nginx 128 MB"],
          ["Secrets volume", "Owned by the Java UID, mode 0400, mounted read-only"],
        ],
        source: ["infra/docker-compose.public.yml", "scripts/public_demo.py (init, validate)"],
      },
    },
    {
      id: "sec-isolation",
      number: "7",
      title: "Container isolation",
      tech: "Compose · loopback ports",
      icon: Container,
      tone: "ops",
      x: 628,
      y: 438,
      w: 580,
      h: 248,
      bullets: [
        "One bridge network for all six services",
        "Ports bind to 127.0.0.1; demo-runtime is private",
        "Java and Python images run as non-root users",
        "Named volumes keep Kafka and PostgreSQL data",
      ],
      deployments: ["local"],
      detail: {
        summary:
          "The local stack favors inspectability: services publish loopback ports so developers can query them directly. It is not a hardened deployment.",
        source: ["infra/docker-compose.yml"],
      },
    },
  ],
  edges: [
    { id: "x-1", from: "sec-edge", to: "sec-gateway", fromSide: "right", toSide: "left", kind: "request", detail: { summary: "Only forwarded requests to the gateway hostname continue." } },
    { id: "x-2", from: "sec-gateway", to: "sec-session", fromSide: "right", toSide: "left", kind: "request", detail: { summary: "Only allowlisted demo routes within rate limits reach Java." } },
    { id: "x-3", from: "sec-session", to: "sec-contract", fromSide: "right", toSide: "left", kind: "request", detail: { summary: "Only authenticated, CSRF-checked, quota-admitted requests reach the controller." } },
    { id: "x-4", from: "sec-contract", to: "sec-authority", fromSide: "bottom", toSide: "top", toOffset: 80, via: [[1067, 372], [247, 372]], kind: "request", label: "accepted request", labelAt: [660, 372], detail: { summary: "A valid request enters the workflow, where authority and integrity rules apply to every component." } },
    { id: "x-5", from: "sec-authority", to: "sec-integrity", fromSide: "right", toSide: "left", kind: "data", detail: { summary: "Every advisory output is persisted as evidence." } },
  ],
  steps: [
    { title: "Reach the edge", text: "Public traffic terminates at Cloudflare and arrives through a tunnel the Mac opened; locally, every port is bound to loopback.", anchor: "sec-edge", nodes: ["sec-edge"], edges: ["x-1"] },
    { title: "Pass the gateway", text: "nginx answers anything outside the exact demo routes with 404, rate-limits the rest, and adds CSP and no-store headers.", anchor: "sec-gateway", nodes: ["sec-gateway"], edges: ["x-2"] },
    { title: "Prove the session", text: "Java verifies the signed cookie against its database row, consumes quotas, and checks CSRF and Origin on every mutation.", anchor: "sec-session", nodes: ["sec-session"], edges: ["x-3"] },
    { title: "Match the contract", text: "Exact fields, bounded values, idempotency and ownership are enforced before any service is called.", anchor: "sec-contract", nodes: ["sec-contract"], edges: ["x-4"], stages: ["submission"] },
    { title: "Hold no authority", text: "Every response that claims authority is rejected, and an approval only records a fictional decision.", anchor: "sec-authority", nodes: ["sec-authority"], edges: ["x-5"], stages: ["decision"] },
    { title: "Keep evidence honest", text: "Stage writes are transactional and journaled; verification gates decisions and deletions.", anchor: "sec-integrity", nodes: ["sec-integrity"], edges: [], stages: ["audit"] },
    { title: "Contain everything", text: "Network, user, privilege, memory and secret boundaries limit what any single component can reach.", anchor: "sec-isolation", nodes: ["sec-isolation"], edges: [] },
  ],
};

// ---------------------------------------------------------------------------
// 6. Audit chain: how the journal is hashed and verified.
// ---------------------------------------------------------------------------
const producerFor: Record<StageId, string> = {
  submission: "Java control plane",
  publication: "Kafka producer / Java control plane",
  ingestion: "Kafka consumer / Java control plane",
  snapshot: "Python evidence projection",
  score: "Python released-model inference",
  rules: "Java control plane",
  allocation: "Java control plane",
  case: "Java control plane",
  agent: "Python bounded agent workflow",
  decision: "Human reviewer / Java control plane",
  audit: "PostgreSQL / Java SHA-256 verifier",
};
const journalStages: StageId[] = [
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
const auditLens: ChainLens = {
  kind: "chain",
  ...lensMeta("audit"),
  title: "A hash chain over every recorded transition",
  summary:
    "How each journal entry is hashed onto the previous one, and the nine checks the verifier runs before a decision, on request, and before deletion.",
  reading:
    "Each block is one journal row. Its hash covers the previous hash and the exact stored payload bytes, so changing any earlier row breaks every later link.",
  expected: [
    { type: "submission.completed", producer: producerFor.submission },
    ...journalStages.flatMap((stage) => [
      { type: `${stage}.processing`, producer: producerFor[stage] },
      {
        type: stage === "agent" ? "agent.completed | agent.abstained" : `${stage}.completed`,
        producer: producerFor[stage],
      },
    ]),
  ],
  checks: [
    { id: "sequence", title: "Contiguous sequence", text: "Entries start at 1 and increase by exactly one.", codes: ["JOURNAL_SEQUENCE_MISMATCH"] },
    { id: "parent", title: "Parent link", text: "Each parent_hash equals the previous current_hash; the first parent is 64 zeros.", codes: ["JOURNAL_PARENT_MISMATCH"] },
    { id: "hash", title: "Recomputed hash", text: "SHA-256(parent_hash + \"\\n\" + canonical_payload) must equal current_hash for every row.", codes: ["JOURNAL_HASH_MISMATCH"] },
    { id: "checkpoint", title: "Checkpoint", text: "The final sequence and head hash must equal the demo_checkpoint row.", codes: ["CHECKPOINT_MISMATCH"] },
    { id: "metadata", title: "Row metadata", text: "Event ID, stage, event type, producer, run and source event in the row must match the hashed payload.", codes: ["JOURNAL_METADATA_MISMATCH"] },
    { id: "time", title: "Timestamps", text: "Row and payload timestamps must agree within 500 nanoseconds.", codes: ["JOURNAL_TIMESTAMP_MISMATCH"] },
    { id: "displayed", title: "Displayed stages", text: "Every completed stage you see equals its committed journal evidence, and every committed stage is still displayed.", codes: ["DISPLAYED_STAGE_SCHEMA_MISMATCH", "DISPLAYED_STAGE_EVIDENCE_MISMATCH"] },
    { id: "artifacts", title: "Artifacts", text: "Score, rules, allocation, agent, decision, snapshot and projection equal their committed evidence.", codes: ["ARTIFACT_EVIDENCE_MISMATCH", "SNAPSHOT_EVIDENCE_MISMATCH", "PROJECTION_EVIDENCE_MISMATCH"] },
    { id: "case", title: "Case provenance", text: "The demo_case row and case version equal the committed case plus the recorded decision.", codes: ["PERSISTED_CASE_EVIDENCE_MISMATCH", "CASE_VERSION_PROVENANCE_MISMATCH"] },
  ],
  when: [
    "Before a human decision is accepted",
    "Inside the decision transaction, as the audit stage",
    "On GET /runs/{id}/audit from the Audit trail view",
    "Before public retention deletes a terminal run",
  ],
  scope: [
    "Detects the tested corruption modes inside the verified scope.",
    "The checkpoint shares PostgreSQL's trust domain; nothing is externally anchored or KMS-signed.",
    "A database administrator who rewrites every row and the checkpoint is not detected.",
  ],
};

// ---------------------------------------------------------------------------
// 7. Database schema: the visitor journey tables (Flyway V6–V8).
// ---------------------------------------------------------------------------
const TABLE_W = 238;
const tableHeight = (columns: number) => 52 + columns * 18 + 10;
const table = (
  id: string,
  x: number,
  y: number,
  columns: Column[],
  detail: Detail,
  live?: LiveProbe,
  stages?: StageId[],
): ArchNode => ({
  id,
  title: id,
  tech: columns.length + " columns",
  icon: Table2,
  tone: "data",
  x,
  y,
  w: TABLE_W,
  h: tableHeight(columns.length),
  columns,
  detail,
  live,
  stages,
});
const schemaLens: GraphLens = {
  kind: "graph",
  ...lensMeta("schema"),
  title: "Eleven tables behind every run",
  summary:
    "The PostgreSQL tables the visitor journey writes, their keys, and how they relate. Created by Flyway migrations V6, V7 and V8.",
  reading:
    "Lines are foreign keys, pointing at the referenced table. Bound to a run, the inspector shows this run's values for each table.",
  width: 1240,
  height: 900,
  stepsTitle: "Write path",
  focus: {
    submission: "demo_run",
    publication: "demo_outbox",
    ingestion: "demo_inbox",
    case: "demo_case",
    decision: "demo_decision",
    audit: "demo_journal",
  },
  groups: [
    { id: "g-tables", label: "inforsight_enterprise", caption: "PostgreSQL 16 · Flyway V6–V8", x: 12, y: 18, w: 1216, h: 868, variant: "zone" },
  ],
  nodes: [
    table(
      "demo_session",
      40,
      300,
      [
        { name: "session_id", type: "text", key: "PK" },
        { name: "created_at", type: "timestamptz" },
        { name: "last_seen_at", type: "timestamptz" },
        { name: "expires_at", type: "timestamptz" },
      ],
      {
        summary:
          "One row per anonymous public visitor. The signed cookie must match a live row; expired sessions without runs or receipts are deleted.",
        source: [`${MIGRATIONS}/V8__public_demo_sessions.sql`],
      },
      "t_session",
    ),
    table(
      "demo_run",
      502,
      280,
      [
        { name: "correlation_id", type: "text", key: "PK" },
        { name: "event_id", type: "text", key: "UQ" },
        { name: "idempotency_key", type: "text", key: "UQ" },
        { name: "request_digest", type: "text" },
        { name: "status", type: "text" },
        { name: "document", type: "jsonb" },
        { name: "owner_session_id", type: "text", key: "FK" },
        { name: "created_at", type: "timestamptz" },
        { name: "updated_at", type: "timestamptz" },
        { name: "last_accessed_at", type: "timestamptz" },
      ],
      {
        summary:
          "The run aggregate. document is the complete JSON the browser polls: stages, artifacts, source history and status. Every writer locks this row with FOR UPDATE.",
        facts: [["Index", "demo_run_owner_status (owner_session_id, status)"]],
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`, `${MIGRATIONS}/V8__public_demo_sessions.sql`],
      },
      "t_run",
      ["submission"],
    ),
    table(
      "demo_outbox",
      280,
      40,
      [
        { name: "event_id", type: "text", key: "PK FK" },
        { name: "correlation_id", type: "text", key: "FK" },
        { name: "envelope", type: "jsonb" },
        { name: "published_at", type: "timestamptz" },
        { name: "attempts", type: "integer" },
        { name: "last_error", type: "text" },
      ],
      {
        summary:
          "The transactional outbox. Written with the run, read by the worker, and marked published after the broker acknowledges. At most 3 send attempts between explicit retries.",
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`],
      },
      "t_outbox",
      ["publication"],
    ),
    table(
      "demo_inbox",
      724,
      40,
      [
        { name: "event_id", type: "text", key: "PK FK" },
        { name: "correlation_id", type: "text", key: "FK" },
        { name: "topic", type: "text" },
        { name: "partition_id", type: "integer" },
        { name: "record_offset", type: "bigint" },
        { name: "received_at", type: "timestamptz" },
      ],
      {
        summary:
          "The durable receipt of a broker delivery. The primary key on event_id makes redelivery a no-op (ON CONFLICT DO NOTHING).",
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`],
      },
      "t_inbox",
      ["ingestion"],
    ),
    table(
      "demo_case",
      966,
      250,
      [
        { name: "case_id", type: "text", key: "PK" },
        { name: "correlation_id", type: "text", key: "UQ FK" },
        { name: "version", type: "bigint" },
        { name: "state", type: "text" },
        { name: "evidence", type: "jsonb" },
        { name: "updated_at", type: "timestamptz" },
      ],
      {
        summary:
          "The reviewable case. evidence holds the four upstream digests; version and state change only through a human decision.",
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`],
      },
      "t_case",
      ["case"],
    ),
    table(
      "demo_decision",
      966,
      460,
      [
        { name: "correlation_id", type: "text", key: "PK FK" },
        { name: "idempotency_key", type: "text", key: "PK" },
        { name: "request_digest", type: "text" },
        { name: "response", type: "jsonb" },
      ],
      {
        summary:
          "Idempotency for human decisions: the same key and body replays the committed response; a different body conflicts.",
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`],
      },
      "t_decision",
      ["decision"],
    ),
    table(
      "demo_journal",
      380,
      620,
      [
        { name: "correlation_id", type: "text", key: "PK FK" },
        { name: "sequence", type: "bigint", key: "PK" },
        { name: "event_id", type: "text", key: "UQ" },
        { name: "stage", type: "text" },
        { name: "event_type", type: "text" },
        { name: "occurred_at", type: "timestamptz" },
        { name: "producer", type: "text" },
        { name: "canonical_payload", type: "text" },
        { name: "parent_hash", type: "text" },
        { name: "current_hash", type: "text" },
      ],
      {
        summary:
          "The append-only evidence journal. The trigger demo_journal_append_only rejects UPDATE and DELETE except verified whole-run retention.",
        facts: [["Hash", "current_hash = SHA-256(parent_hash + '\\n' + canonical_payload)"]],
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`, `${MIGRATIONS}/V8__public_demo_sessions.sql`],
      },
      "t_journal",
      ["audit"],
    ),
    table(
      "demo_checkpoint",
      660,
      680,
      [
        { name: "correlation_id", type: "text", key: "PK FK" },
        { name: "sequence", type: "bigint" },
        { name: "head_hash", type: "text" },
      ],
      {
        summary:
          "The latest sequence and head hash for each run, upserted with every journal append and compared during verification.",
        source: [`${MIGRATIONS}/V6__durable_demo_journey.sql`],
      },
      "t_checkpoint",
      ["audit"],
    ),
    table(
      "demo_retention_receipt",
      40,
      520,
      [
        { name: "correlation_id", type: "text", key: "PK" },
        { name: "owner_session_id", type: "text", key: "FK" },
        { name: "deleted_at", type: "timestamptz" },
        { name: "verified_entries", type: "bigint" },
        { name: "last_verified_head", type: "text" },
        { name: "verification_valid", type: "boolean ✓" },
      ],
      {
        summary:
          "Proof that a run was verified before deletion. Kept for 7 days so its owner gets 410 Gone instead of 404. A CHECK constraint requires verification_valid.",
        source: [`${MIGRATIONS}/V8__public_demo_sessions.sql`],
      },
    ),
    table(
      "demo_quota",
      966,
      650,
      [
        { name: "subject", type: "text", key: "PK" },
        { name: "operation", type: "text", key: "PK" },
        { name: "window_start", type: "bigint", key: "PK" },
        { name: "used", type: "integer" },
        { name: "updated_at", type: "timestamptz" },
      ],
      {
        summary:
          "Fixed-window counters per session (or * for global) and operation. Serialized by an advisory lock; rows idle for 48 hours are deleted.",
        source: [`${MIGRATIONS}/V8__public_demo_sessions.sql`, `${JAVA}/demo/DemoPublicAccess.java`],
      },
    ),
    table(
      "demo_ingress_quarantine",
      40,
      720,
      [
        { name: "topic", type: "text", key: "PK" },
        { name: "partition_id", type: "integer", key: "PK" },
        { name: "record_offset", type: "bigint", key: "PK" },
        { name: "payload_sha256", type: "text" },
        { name: "error_code", type: "text" },
      ],
      {
        summary:
          "Broker records that failed validation, stored only as a digest and error code (never the untrusted payload) so their offset can be committed safely. Kept 7 days.",
        source: [`${MIGRATIONS}/V7__demo_ingress_quarantine.sql`],
      },
    ),
  ],
  edges: [
    { id: "fk-outbox", from: "demo_outbox", to: "demo_run", fromSide: "bottom", toSide: "top", toOffset: -60, kind: "data", label: "event_id · correlation_id", stages: ["publication"], detail: { summary: "demo_outbox.event_id → demo_run.event_id and demo_outbox.correlation_id → demo_run." } },
    { id: "fk-inbox", from: "demo_inbox", to: "demo_run", fromSide: "bottom", toSide: "top", toOffset: 60, kind: "data", label: "event_id · correlation_id", stages: ["ingestion"], detail: { summary: "demo_inbox.event_id → demo_run.event_id and demo_inbox.correlation_id → demo_run." } },
    { id: "fk-case", from: "demo_case", to: "demo_run", fromSide: "left", toSide: "right", toOffset: -40, kind: "data", label: "correlation_id", stages: ["case"], detail: { summary: "demo_case.correlation_id → demo_run (unique: one case per run)." } },
    { id: "fk-decision", from: "demo_decision", to: "demo_run", fromSide: "left", toSide: "right", toOffset: 70, kind: "data", label: "correlation_id", stages: ["decision"], detail: { summary: "demo_decision.correlation_id → demo_run." } },
    { id: "fk-journal", from: "demo_journal", to: "demo_run", fromSide: "top", toSide: "bottom", fromOffset: 40, toOffset: -40, kind: "data", label: "correlation_id", stages: ["audit"], detail: { summary: "demo_journal.correlation_id → demo_run." } },
    { id: "fk-checkpoint", from: "demo_checkpoint", to: "demo_run", fromSide: "top", toSide: "bottom", toOffset: 70, kind: "data", label: "correlation_id", stages: ["audit"], detail: { summary: "demo_checkpoint.correlation_id → demo_run (one row per run)." } },
    { id: "fk-owner", from: "demo_run", to: "demo_session", fromSide: "left", toSide: "right", kind: "data", label: "owner_session_id", detail: { summary: "demo_run.owner_session_id → demo_session (public mode)." } },
    { id: "fk-receipt", from: "demo_retention_receipt", to: "demo_session", fromSide: "top", toSide: "bottom", kind: "data", label: "owner_session_id", detail: { summary: "demo_retention_receipt.owner_session_id → demo_session." } },
  ],
  steps: [
    { title: "Accept", text: "Submission inserts demo_run and demo_outbox in one transaction and appends journal entry 1 with its checkpoint.", anchor: "demo_run", nodes: ["demo_run", "demo_outbox", "demo_journal", "demo_checkpoint"], edges: ["fk-outbox"], stages: ["submission"] },
    { title: "Publish and receive", text: "The outbox row is marked published; the delivery is recorded once in demo_inbox. Invalid records only reach demo_ingress_quarantine.", anchor: "demo_inbox", nodes: ["demo_outbox", "demo_inbox", "demo_ingress_quarantine"], edges: ["fk-outbox", "fk-inbox"], stages: ["publication", "ingestion"] },
    { title: "Persist evidence", text: "Each stage rewrites demo_run.document and appends to demo_journal; the case stage inserts demo_case.", anchor: "demo_case", nodes: ["demo_run", "demo_case", "demo_journal"], edges: ["fk-case", "fk-journal"], stages: ["case"] },
    { title: "Decide", text: "The decision updates demo_case, appends journal entries, and stores the replayable response in demo_decision.", anchor: "demo_decision", nodes: ["demo_case", "demo_decision", "demo_journal", "demo_checkpoint"], edges: ["fk-decision", "fk-checkpoint"], stages: ["decision", "audit"] },
    { title: "Own and limit", text: "In public mode, demo_session owns runs and demo_quota counts requests, submissions, polls, retries and decisions.", anchor: "demo_session", nodes: ["demo_session", "demo_quota", "demo_run"], edges: ["fk-owner"] },
    { title: "Retain and delete", text: "Verified terminal runs are deleted table by table after a receipt is written; the receipt lets the owner see 410 Gone.", anchor: "demo_retention_receipt", nodes: ["demo_retention_receipt", "demo_session"], edges: ["fk-receipt"] },
  ],
};

export const lenses: Lens[] = [
  systemLens,
  sequenceLens,
  lineageLens,
  lifecycleLens,
  securityLens,
  auditLens,
  schemaLens,
];
export const lensIds = lenses.map((lens) => lens.id);

export function visibleIn<T extends { deployments?: Deployment[] }>(
  items: T[],
  deployment: Deployment,
): T[] {
  return items.filter((item) => !item.deployments || item.deployments.includes(deployment));
}

/** Glanceable facts for orientation; each is derived from repository configuration. */
export const atAGlance: { value: string; label: string }[] = [
  { value: "6 · 7", label: "containers locally · in the Mac preview" },
  { value: "11", label: "persisted checkpoints per run" },
  { value: "1", label: "Kafka topic, one partition" },
  { value: "11", label: "demo_* tables in PostgreSQL" },
  { value: "17 → 28", label: "features → model columns" },
  { value: "21", label: "hashed journal entries per completed run" },
];
