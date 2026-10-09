import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Check,
  Cloud,
  Fingerprint,
  Globe,
  Info,
  Laptop,
  Link2,
  Maximize2,
  Pause,
  Play,
  RefreshCw,
  ShieldCheck,
  X,
  type LucideIcon,
} from "./icons";
import {
  date,
  duration,
  object,
  text,
  words,
  type Audit,
  type Evidence,
  type Run,
  type ScenarioCatalog,
  type VisitorSession,
} from "./api";
import { flowSteps } from "./flow-model";
import {
  atAGlance,
  edgeKindLabels,
  lenses,
  lensIds,
  toneLabels,
  visibleIn,
  type ArchEdge,
  type ArchNode,
  type ArchStep,
  type Band,
  type ChainLens,
  type Deployment,
  type Detail,
  type GraphLens,
  type Lens,
  type LensId,
  type Message,
  type SequenceLens,
  type Side,
} from "./architecture-model";
import {
  currentStage,
  liveFacts,
  liveSummary,
  passedStates,
  stageCount,
  stageOf,
  stageState,
  stateLabel,
  terminal,
  type Connection,
  type Fact,
  type LiveContext,
  type LiveState,
} from "./architecture-live";
import "./architecture.css";

type SelectionKind =
  | "node"
  | "edge"
  | "step"
  | "participant"
  | "message"
  | "band"
  | "entry"
  | "check";
type Selection = { kind: SelectionKind; id: string };
type Walk = { lens: LensId; index: number; playing: boolean; inspect?: Selection };
type Point = [number, number];

const stageTitle = (id: string) =>
  flowSteps.find((step) => step.id === id)?.title ?? words(id);
const lensById = (id: LensId) => lenses.find((lens) => lens.id === id)!;
const WALK_DELAY: Record<Lens["kind"], number> = { graph: 2800, sequence: 1300, chain: 900 };

function lensFromUrl(): LensId {
  const value = new URLSearchParams(window.location.search).get("lens");
  return lensIds.includes(value as LensId) ? (value as LensId) : "system";
}

// ---------------------------------------------------------------------------
// Geometry: orthogonal routes with rounded corners between node anchors.
// ---------------------------------------------------------------------------
function anchor(node: ArchNode, side: Side, offset = 0): Point {
  if (side === "top") return [node.x + node.w / 2 + offset, node.y];
  if (side === "bottom") return [node.x + node.w / 2 + offset, node.y + node.h];
  if (side === "left") return [node.x, node.y + node.h / 2 + offset];
  return [node.x + node.w, node.y + node.h / 2 + offset];
}
function routePoints(edge: ArchEdge, from: ArchNode, to: ArchNode): Point[] {
  const start = anchor(from, edge.fromSide, edge.fromOffset);
  const end = anchor(to, edge.toSide, edge.toOffset);
  const raw: Point[] = (() => {
    if (edge.via) return [start, ...edge.via, end];
    const horizontalStart = edge.fromSide === "left" || edge.fromSide === "right";
    const horizontalEnd = edge.toSide === "left" || edge.toSide === "right";
    if (horizontalStart && horizontalEnd) {
      if (start[1] === end[1]) return [start, end];
      const middle = (start[0] + end[0]) / 2;
      return [start, [middle, start[1]], [middle, end[1]], end];
    }
    if (!horizontalStart && !horizontalEnd) {
      if (start[0] === end[0]) return [start, end];
      const middle = (start[1] + end[1]) / 2;
      return [start, [start[0], middle], [end[0], middle], end];
    }
    return horizontalStart ? [start, [end[0], start[1]], end] : [start, [start[0], end[1]], end];
  })();
  return raw.filter(
    (point, index) =>
      index === 0 || point[0] !== raw[index - 1][0] || point[1] !== raw[index - 1][1],
  );
}
function roundedPath(points: Point[], radius = 10): string {
  let path = `M ${points[0][0]} ${points[0][1]}`;
  for (let index = 1; index < points.length - 1; index++) {
    const [px, py] = points[index - 1];
    const [cx, cy] = points[index];
    const [nx, ny] = points[index + 1];
    const into = Math.hypot(cx - px, cy - py);
    const out = Math.hypot(nx - cx, ny - cy);
    const r = Math.min(radius, into / 2, out / 2);
    path += ` L ${cx - ((cx - px) / into) * r} ${cy - ((cy - py) / into) * r}`;
    path += ` Q ${cx} ${cy} ${cx + ((nx - cx) / out) * r} ${cy + ((ny - cy) / out) * r}`;
  }
  const last = points[points.length - 1];
  return `${path} L ${last[0]} ${last[1]}`;
}
function midpoint(points: Point[]): Point {
  let best = 0;
  let longest = -1;
  for (let index = 0; index < points.length - 1; index++) {
    const length = Math.hypot(
      points[index + 1][0] - points[index][0],
      points[index + 1][1] - points[index][1],
    );
    if (length > longest) {
      longest = length;
      best = index;
    }
  }
  return [
    (points[best][0] + points[best + 1][0]) / 2,
    (points[best][1] + points[best + 1][1]) / 2,
  ];
}

// ---------------------------------------------------------------------------
// Small presentational pieces.
// ---------------------------------------------------------------------------
function IconButton({
  label,
  onClick,
  disabled,
  pressed,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  pressed?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className="arch-icon-button"
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

function Facts({ facts, className = "" }: { facts: Fact[]; className?: string }) {
  return (
    <dl className={`arch-facts ${className}`}>
      {facts.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function DetailBody({ detail, live }: { detail: Detail; live?: Fact[] | null }) {
  return (
    <>
      <p className="arch-inspector-summary">{detail.summary}</p>
      {live && (
        <section className="arch-live-evidence" aria-label="Live evidence">
          <h4>
            <span className="arch-live-dot" aria-hidden="true" />
            Live evidence
          </h4>
          <Facts facts={live} />
        </section>
      )}
      {detail.facts && (
        <section>
          <h4>Key facts</h4>
          <Facts facts={detail.facts} />
        </section>
      )}
      {detail.sections?.map((section) => (
        <section key={section.title}>
          <h4>{section.title}</h4>
          <ul className="arch-bullets">
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
      {detail.source && (
        <section>
          <h4>Where it lives</h4>
          <ul className="arch-source">
            {detail.source.map((path) => (
              <li key={path}>
                <code>{path}</code>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Graph canvas: system map, lineage, lifecycle, security and schema lenses.
// ---------------------------------------------------------------------------
type NodeView = { state: LiveState | "current" | "passed"; pill?: string };

function nodeView(lens: GraphLens, node: ArchNode, context: LiveContext): NodeView {
  const { run } = context;
  if (!run) return { state: "idle" };
  if (lens.id === "lifecycle") {
    if (node.id.startsWith("st-")) {
      const status = node.id.slice(3) as Parameters<typeof stageCount>[1];
      const total = stageCount(run, status);
      return total ? { state: "current", pill: `${total} of ${run.stages.length}` } : { state: "idle" };
    }
    const caseState = text(object(run.artifacts.case).state, "");
    const states = node.states ?? [];
    const isCase = node.id.startsWith("cs-");
    if (isCase ? states.includes(caseState) : states.includes(run.status))
      return { state: "current", pill: "current" };
    const passed = passedStates(run);
    if (states.some((state) => passed.has(isCase ? `case:${state}` : state)))
      return { state: "passed", pill: "passed" };
    return { state: "idle" };
  }
  if (!node.stages?.length) return { state: "idle" };
  const { state, recorded, total } = stageState(run, node.stages);
  return { state, pill: stateLabel(state, recorded, total) };
}

function GraphCanvas({
  lens,
  deployment,
  context,
  selection,
  highlight,
  flowing,
  motion,
  paused,
  stepNumbers,
  onSelect,
  focusNode,
}: {
  lens: GraphLens;
  deployment: Deployment;
  context: LiveContext;
  selection?: Selection;
  highlight?: ArchStep;
  flowing: Set<string>;
  motion: boolean;
  paused: boolean;
  stepNumbers: Map<string, number[]>;
  onSelect: (selection: Selection) => void;
  focusNode: (id: string) => void;
}) {
  const nodes = visibleIn(lens.nodes, deployment);
  const groups = visibleIn(lens.groups, deployment);
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const edges = visibleIn(lens.edges, deployment).filter(
    (edge) => byId.has(edge.from) && byId.has(edge.to),
  );
  const selectedNode = selection?.kind === "node" ? selection.id : undefined;
  const live = Boolean(context.run);
  return (
    <div
      className="arch-scene"
      style={{ width: lens.width, height: lens.height }}
      data-testid={`arch-canvas-${lens.id}`}
    >
      {groups.map((group) => (
        <div
          key={`${group.id}-${group.label}`}
          className={`arch-group is-${group.variant}`}
          style={{ left: group.x, top: group.y, width: group.w, height: group.h }}
        >
          <span className="arch-group-label">
            {group.variant === "private" && <LockSymbol />}
            {group.label}
          </span>
          {group.caption && <span className="arch-group-caption">{group.caption}</span>}
        </div>
      ))}
      <svg
        className="arch-edges"
        viewBox={`0 0 ${lens.width} ${lens.height}`}
        width={lens.width}
        height={lens.height}
        aria-hidden="true"
      >
        <defs>
          {["request", "event", "data", "control", "active", "muted"].map((kind) => (
            <marker
              key={kind}
              id={`arch-m-${kind}`}
              className={`arch-marker is-${kind}`}
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" />
            </marker>
          ))}
        </defs>
        {edges.map((edge) => {
          const points = routePoints(edge, byId.get(edge.from)!, byId.get(edge.to)!);
          const path = roundedPath(points);
          const stage = live ? stageState(context.run, edge.stages) : undefined;
          const active = flowing.has(edge.id);
          const inStep = highlight?.edges.includes(edge.id);
          const related = selectedNode && (edge.from === selectedNode || edge.to === selectedNode);
          const muted = Boolean(highlight) && !inStep;
          const marker = active || inStep ? "active" : muted ? "muted" : edge.kind;
          return (
            <g
              key={edge.id}
              data-testid={`arch-edge-${edge.id}`}
              className={[
                "arch-edge",
                `is-${edge.kind}`,
                active ? "is-flowing" : "",
                inStep ? "is-step" : "",
                related ? "is-related" : "",
                muted ? "is-muted" : "",
                stage && stage.state === "recorded" ? "is-recorded" : "",
                stage && stage.state === "failed" ? "is-failed" : "",
                paused ? "is-paused" : "",
              ].join(" ")}
            >
              <path
                className="arch-edge-path"
                d={path}
                markerEnd={`url(#arch-m-${marker})`}
                markerStart={edge.twoWay ? `url(#arch-m-${marker})` : undefined}
              />
              {(active || inStep) && motion && !paused && (
                <>
                  <circle className="arch-packet" r="3.6">
                    <animateMotion dur="1.9s" repeatCount="indefinite" path={path} />
                  </circle>
                  {edge.twoWay && (
                    <circle className="arch-packet is-return" r="3.2">
                      <animateMotion
                        dur="1.9s"
                        begin="0.95s"
                        repeatCount="indefinite"
                        path={path}
                        keyPoints="1;0"
                        keyTimes="0;1"
                        calcMode="linear"
                      />
                    </circle>
                  )}
                </>
              )}
            </g>
          );
        })}
      </svg>
      {edges.map((edge) => {
        const numbers = stepNumbers.get(edge.id) ?? [];
        if (!edge.label && !numbers.length) return null;
        const points = routePoints(edge, byId.get(edge.from)!, byId.get(edge.to)!);
        const [x, y] = edge.labelAt ?? midpoint(points);
        const from = byId.get(edge.from)!;
        const to = byId.get(edge.to)!;
        return (
          <button
            type="button"
            key={edge.id}
            data-testid={`arch-edge-label-${edge.id}`}
            className={[
              "arch-edge-label",
              `is-${edge.kind}`,
              selection?.kind === "edge" && selection.id === edge.id ? "is-selected" : "",
              highlight && !highlight.edges.includes(edge.id) ? "is-muted" : "",
              flowing.has(edge.id) || highlight?.edges.includes(edge.id) ? "is-active" : "",
            ].join(" ")}
            style={{ left: x, top: y }}
            aria-label={`Connection: ${from.title} to ${to.title}${edge.label ? `, ${edge.label}` : ""}${numbers.length ? `, dataflow step ${numbers.join(" and ")}` : ""}`}
            onClick={() => onSelect({ kind: "edge", id: edge.id })}
          >
            {numbers.map((number) => (
              <span className="arch-step-badge" key={number} aria-hidden="true">
                {number}
              </span>
            ))}
            {edge.label}
          </button>
        );
      })}
      {nodes.map((node, index) => {
        const view = nodeView(lens, node, context);
        const summary = liveSummary(node.live, context);
        const inStep = highlight?.nodes.includes(node.id);
        const numbers = stepNumbers.get(node.id) ?? [];
        const mini = node.h < 80;
        const compact = node.w < 160 && !mini;
        return (
          <button
            type="button"
            key={node.id}
            data-testid={`arch-node-${node.id}`}
            data-status={view.state}
            data-tone={node.tone}
            className={[
              "arch-node",
              `tone-${node.tone}`,
              `is-${view.state}`,
              compact ? "is-compact" : "",
              mini ? "is-mini" : "",
              node.mono ? "is-mono" : "",
              node.columns ? "is-table" : "",
              selectedNode === node.id ? "is-selected" : "",
              inStep ? "is-step" : "",
              highlight && !inStep ? "is-muted" : "",
            ].join(" ")}
            style={{ left: node.x, top: node.y, width: node.w, height: node.h }}
            aria-pressed={selectedNode === node.id}
            aria-label={`${node.title.replace("​", "")}, ${node.tech}.${view.pill ? ` Status: ${view.pill}.` : ""}${summary ? ` ${summary}.` : ""}`}
            onClick={() => onSelect({ kind: "node", id: node.id })}
            onKeyDown={(event) => {
              const offset =
                event.key === "ArrowRight" || event.key === "ArrowDown"
                  ? 1
                  : event.key === "ArrowLeft" || event.key === "ArrowUp"
                    ? -1
                    : 0;
              const target =
                event.key === "Home" ? 0 : event.key === "End" ? nodes.length - 1 : offset ? (index + offset + nodes.length) % nodes.length : -1;
              if (target < 0) return;
              event.preventDefault();
              onSelect({ kind: "node", id: nodes[target].id });
              focusNode(nodes[target].id);
            }}
          >
            {node.number && <span className="arch-node-number">{node.number}</span>}
            {numbers.map((number) => (
              <span className="arch-step-badge is-node" key={number} aria-hidden="true">
                {number}
              </span>
            ))}
            <span className="arch-node-head">
              <span className="arch-node-icon">
                <node.icon size={mini ? 14 : compact ? 16 : 18} aria-hidden="true" />
              </span>
              <span className="arch-node-titles">
                <span className="arch-node-title">{node.title}</span>
                {!node.columns && <span className="arch-node-tech">{node.tech}</span>}
              </span>
              {view.pill && (
                <span className={`arch-node-pill is-${view.state}`}>{view.pill}</span>
              )}
            </span>
            {node.bullets && (
              <span className="arch-node-bullets">
                {node.bullets.map((bullet) => (
                  <span className="arch-node-bullet" key={bullet}>
                    {bullet}
                  </span>
                ))}
              </span>
            )}
            {node.columns && (
              <span className="arch-columns">
                {node.columns.map((column) => (
                  <span className="arch-column" key={column.name}>
                    <span className="arch-column-key">{column.key ?? ""}</span>
                    <span className="arch-column-name">{column.name}</span>
                    <span className="arch-column-type">{column.type}</span>
                  </span>
                ))}
              </span>
            )}
            {(node.chips?.length || summary) && (
              <span className="arch-node-foot">
                {node.chips?.map((chip) => (
                  <span className="arch-chip" key={chip}>
                    {chip}
                  </span>
                ))}
                {summary && (
                  <span className={`arch-live-chip is-${view.state}`}>
                    <span className="arch-live-dot" aria-hidden="true" />
                    {summary}
                  </span>
                )}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function LockSymbol() {
  return (
    <svg className="arch-lock" viewBox="0 0 12 12" aria-hidden="true">
      <rect x="2" y="5.5" width="8" height="5.5" rx="1.2" />
      <path d="M4 5.5V4a2 2 0 0 1 4 0v1.5" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Sequence canvas: participants, stage bands and numbered messages.
// ---------------------------------------------------------------------------
const SEQ_WIDTH = 1060;
const SEQ_HEADER = 70;
const BAND_HEIGHT = 32;
const ROW_HEIGHT = 34;
const lifelineX = (index: number) => 72 + index * 131;
type SequenceRow =
  | { kind: "band"; band: Band; y: number; height: number }
  | { kind: "message"; band: Band; message: Message; number: number; y: number };

function sequenceRows(lens: SequenceLens) {
  const rows: SequenceRow[] = [];
  let y = 10;
  let number = 0;
  for (const band of lens.bands) {
    const height = BAND_HEIGHT + band.messages.length * ROW_HEIGHT + 6;
    rows.push({ kind: "band", band, y, height });
    y += BAND_HEIGHT;
    for (const message of band.messages) {
      number += 1;
      rows.push({ kind: "message", band, message, number, y });
      y += ROW_HEIGHT;
    }
    y += 14;
  }
  return { rows, height: y };
}
export const sequenceMessageCount = (lens: SequenceLens) =>
  lens.bands.reduce((sum, band) => sum + band.messages.length, 0);

function bandState(band: Band, context: LiveContext): LiveState {
  if (!context.run || band.id === "session" || band.id === "polling") return "idle";
  return stageState(context.run, [band.id]).state;
}

function SequenceCanvas({
  lens,
  context,
  selection,
  walkNumber,
  motion,
  onSelect,
}: {
  lens: SequenceLens;
  context: LiveContext;
  selection?: Selection;
  walkNumber?: number;
  motion: boolean;
  onSelect: (selection: Selection) => void;
}) {
  const { rows, height } = useMemo(() => sequenceRows(lens), [lens]);
  const xs = new Map(lens.participants.map((participant, index) => [participant.id, lifelineX(index)]));
  const name = (id: string) => lens.participants.find((participant) => participant.id === id)?.title ?? id;
  return (
    <div
      className="arch-seq-scene"
      style={{ width: SEQ_WIDTH }}
      data-testid="arch-canvas-sequence"
    >
      <div className="arch-seq-header" style={{ width: SEQ_WIDTH, height: SEQ_HEADER }}>
        {lens.participants.map((participant, index) => (
          <button
            type="button"
            key={participant.id}
            className={`arch-participant tone-${participant.tone} ${selection?.kind === "participant" && selection.id === participant.id ? "is-selected" : ""}`}
            style={{ left: lifelineX(index) }}
            aria-pressed={selection?.kind === "participant" && selection.id === participant.id}
            onClick={() => onSelect({ kind: "participant", id: participant.id })}
          >
            <participant.icon size={15} aria-hidden="true" />
            <span>
              <strong>{participant.title}</strong>
              <small>{participant.tech}</small>
            </span>
          </button>
        ))}
      </div>
      <div className="arch-seq-body" style={{ height }}>
        <svg
          className="arch-seq-svg"
          width={SEQ_WIDTH}
          height={height}
          viewBox={`0 0 ${SEQ_WIDTH} ${height}`}
          aria-hidden="true"
        >
          <defs>
            {["call", "return", "async", "active"].map((kind) => (
              <marker
                key={kind}
                id={`arch-seq-${kind}`}
                className={`arch-marker is-${kind}`}
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto"
              >
                {kind === "return" || kind === "async" ? (
                  <path d="M 1 1 L 9 5 L 1 9" fill="none" />
                ) : (
                  <path d="M 0 0 L 10 5 L 0 10 z" />
                )}
              </marker>
            ))}
          </defs>
          {rows.map((row) =>
            row.kind === "band" ? (
              <rect
                key={`band-${row.band.id}`}
                className={`arch-seq-band is-${bandState(row.band, context)}`}
                x={8}
                y={row.y}
                width={SEQ_WIDTH - 16}
                height={row.height}
                rx={7}
              />
            ) : null,
          )}
          {lens.participants.map((participant, index) => (
            <line
              key={participant.id}
              className="arch-lifeline"
              x1={lifelineX(index)}
              x2={lifelineX(index)}
              y1={0}
              y2={height}
            />
          ))}
          {rows.map((row) => {
            if (row.kind !== "message") return null;
            const { message } = row;
            const x1 = xs.get(message.from)!;
            const x2 = xs.get(message.to)!;
            const lineY = row.y + 25;
            const state = bandState(row.band, context);
            const walking = walkNumber === row.number;
            const active = walking || (state === "processing" && context.connection === "connected");
            const path =
              message.kind === "self"
                ? `M ${x1} ${lineY - 9} h 34 v 13 h -32`
                : `M ${x1 + (x2 > x1 ? 3 : -3)} ${lineY} L ${x2 + (x2 > x1 ? -3 : 3)} ${lineY}`;
            return (
              <g
                key={row.number}
                className={[
                  "arch-msg-line",
                  `is-${message.kind}`,
                  `is-${state}`,
                  active ? "is-active" : "",
                  walkNumber !== undefined && row.number < walkNumber ? "is-visited" : "",
                ].join(" ")}
              >
                <path d={path} markerEnd={`url(#arch-seq-${active ? "active" : message.kind === "self" ? "call" : message.kind})`} />
                {active && motion && message.kind !== "self" && (
                  <circle className="arch-packet" r="3.4">
                    <animateMotion dur="1.2s" repeatCount="indefinite" path={path} />
                  </circle>
                )}
              </g>
            );
          })}
        </svg>
        {rows.map((row) => {
          if (row.kind === "band") {
            const state = bandState(row.band, context);
            const stage = row.band.id !== "session" && row.band.id !== "polling" ? stageOf(context.run, row.band.id) : undefined;
            const selected = selection?.kind === "band" && selection.id === row.band.id;
            const stageIndex = flowSteps.findIndex((step) => step.id === row.band.id);
            return (
              <button
                type="button"
                key={`band-${row.band.id}`}
                data-testid={`arch-band-${row.band.id}`}
                data-status={state}
                className={`arch-band-label is-${state} ${selected ? "is-selected" : ""}`}
                style={{ top: row.y + 6 }}
                aria-pressed={selected}
                onClick={() => onSelect({ kind: "band", id: row.band.id })}
              >
                <span className="arch-band-index">
                  {stageIndex >= 0 ? String(stageIndex + 1).padStart(2, "0") : "··"}
                </span>
                <strong>{row.band.title}</strong>
                <span className="arch-band-caption">{row.band.caption}</span>
                {context.run && stage && (
                  <span className={`arch-band-state is-${state}`}>
                    {state === "idle" ? "" : state}
                    {typeof stage.duration_ms === "number" ? ` · ${duration(stage.duration_ms)}` : ""}
                  </span>
                )}
              </button>
            );
          }
          const { message } = row;
          const x1 = xs.get(message.from)!;
          const x2 = xs.get(message.to)!;
          const self = message.kind === "self";
          const center = (x1 + x2) / 2;
          const align = self ? "is-self" : center < 240 ? "is-start" : center > SEQ_WIDTH - 240 ? "is-end" : "";
          const selected = selection?.kind === "message" && selection.id === String(row.number);
          return (
            <button
              type="button"
              key={row.number}
              data-testid={`arch-message-${row.number}`}
              className={`arch-msg ${selected ? "is-selected" : ""} ${walkNumber === row.number ? "is-walking" : ""}`}
              style={{ top: row.y, height: ROW_HEIGHT }}
              aria-pressed={selected}
              aria-label={`Message ${row.number}: ${name(message.from)} ${self ? "internal step" : `to ${name(message.to)}`}: ${message.label}`}
              onClick={() => onSelect({ kind: "message", id: String(row.number) })}
            >
              <span
                className={`arch-msg-label ${align}`}
                style={
                  align === "is-end"
                    ? { right: SEQ_WIDTH - 10 - Math.max(x1, x2) }
                    : { left: self ? x1 + 32 : align === "is-start" ? Math.min(x1, x2) - 6 : center - 10 }
                }
              >
                <span className="arch-msg-number">{row.number}</span>
                {message.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chain canvas: journal blocks and the verifier's checks.
// ---------------------------------------------------------------------------
type ChainBlock = {
  id: string;
  sequence: number;
  type: string;
  producer: string;
  at?: string;
  parent?: string;
  hash?: string;
  payload?: unknown;
};
function chainBlocks(lens: ChainLens, audit: Audit | null): { blocks: ChainBlock[]; live: boolean } {
  const entries = audit?.entries ?? [];
  if (entries.length)
    return {
      live: true,
      blocks: entries.map((entry: Evidence, index) => ({
        id: text(entry.event_id, String(index + 1)),
        sequence: Number(entry.sequence ?? index + 1),
        type: text(entry.event_type, words(entry.stage)),
        producer: text(entry.producer),
        at: text(entry.occurred_at, ""),
        parent: text(entry.parent_hash, ""),
        hash: text(entry.current_hash, ""),
        payload: entry.payload ?? entry.canonical_payload,
      })),
    };
  return {
    live: false,
    blocks: lens.expected.map((item, index) => ({
      id: `expected-${index + 1}`,
      sequence: index + 1,
      type: item.type,
      producer: item.producer,
    })),
  };
}
const shortHash = (value?: string) =>
  value ? `${value.slice(0, 10)}…${value.slice(-4)}` : "computed per run";

function ChainCanvas({
  lens,
  context,
  auditBusy,
  onVerify,
  selection,
  walkIndex,
  onSelect,
}: {
  lens: ChainLens;
  context: LiveContext;
  auditBusy: boolean;
  onVerify: () => void;
  selection?: Selection;
  walkIndex?: number;
  onSelect: (selection: Selection) => void;
}) {
  const { blocks, live } = chainBlocks(lens, context.audit);
  const audit = context.audit;
  const failure = audit && !audit.valid ? audit.failure_code : undefined;
  // A loaded verification describes the chain when it ran, so say when that was.
  const verifiedAt = text(object(audit).verified_at, "");
  return (
    <div className="arch-chain" data-testid="arch-canvas-audit">
      <div className="arch-chain-column">
        <div className="arch-formula">
          <span className="arch-formula-label">Each row</span>
          <code>
            current_hash = SHA-256( parent_hash + "\n" + canonical_payload )
          </code>
          <span className="arch-formula-note">
            The first parent is 64 zeros. Payload bytes are hashed exactly as stored.
          </span>
        </div>
        <div className={`arch-chain-status ${live ? (audit?.valid ? "is-valid" : "is-invalid") : ""}`}>
          {live ? (
            audit?.valid ? <ShieldCheck size={16} aria-hidden="true" /> : <X size={16} aria-hidden="true" />
          ) : (
            <Info size={16} aria-hidden="true" />
          )}
          <span>
            {live
              ? audit?.valid
                ? `This run's chain verified${verifiedAt ? ` at ${date(verifiedAt)}` : ""}: ${text(audit.verified_entries, String(blocks.length))} entries, head ${shortHash(audit.head_hash)}.`
                : `Verification did not pass${failure ? `: ${failure}` : ""}.`
              : context.run
                ? "Load this run's journal to replace the expected sequence with its real rows and hashes."
                : "Expected journal for a completed run. Hashes are computed per run, so none are shown here."}
          </span>
          {context.run && (
            <button type="button" className="arch-chain-load" onClick={onVerify} disabled={auditBusy}>
              <RefreshCw size={13} aria-hidden="true" />
              {auditBusy ? "Verifying…" : live ? "Verify again" : "Load and verify this run's chain"}
            </button>
          )}
        </div>
        <ol className="arch-blocks" aria-label={live ? "Verified journal entries" : "Expected journal entries"}>
          <li className="arch-genesis">
            <span>genesis</span>
            <code>{"0".repeat(16)}…</code>
          </li>
          {blocks.map((block, index) => {
            const selected = selection?.kind === "entry" && selection.id === block.id;
            return (
              <li key={block.id} className={walkIndex === index ? "is-walking" : ""}>
                <button
                  type="button"
                  data-testid={`arch-entry-${block.sequence}`}
                  className={`arch-block ${selected ? "is-selected" : ""} ${live ? "is-live" : ""}`}
                  aria-pressed={selected}
                  onClick={() => onSelect({ kind: "entry", id: block.id })}
                >
                  <span className="arch-block-seq">#{block.sequence}</span>
                  <span className="arch-block-main">
                    <strong>{block.type}</strong>
                    <small>
                      {block.producer}
                      {block.at ? ` · ${date(block.at)}` : ""}
                    </small>
                  </span>
                  <span className="arch-block-hashes">
                    {block.hash ? (
                      <>
                        <code title={block.parent}>parent {shortHash(block.parent)}</code>
                        <code title={block.hash}>hash {shortHash(block.hash)}</code>
                      </>
                    ) : (
                      <code>parent = {index ? `hash #${index}` : "genesis"}</code>
                    )}
                  </span>
                </button>
              </li>
            );
          })}
          <li className="arch-checkpoint">
            <Fingerprint size={15} aria-hidden="true" />
            <span>
              demo_checkpoint · sequence {live ? String(blocks.length) : "N"} · head{" "}
              {live ? shortHash(audit?.head_hash) : "latest hash"}
            </span>
          </li>
        </ol>
      </div>
      <div className="arch-checks">
        <p className="arch-checks-title">The verifier runs nine checks</p>
        <ol>
          {lens.checks.map((check, index) => {
            const failed = failure ? check.codes.includes(failure) : false;
            const state = live ? (audit?.valid ? "passed" : failed ? "failed" : "unknown") : "reference";
            const selected = selection?.kind === "check" && selection.id === check.id;
            return (
              <li key={check.id}>
                <button
                  type="button"
                  data-testid={`arch-check-${check.id}`}
                  className={`arch-check is-${state} ${selected ? "is-selected" : ""}`}
                  aria-pressed={selected}
                  onClick={() => onSelect({ kind: "check", id: check.id })}
                >
                  <span className="arch-check-index">{index + 1}</span>
                  <span>
                    <strong>{check.title}</strong>
                    <small>{check.text}</small>
                  </span>
                  <span className="arch-check-state">
                    {state === "passed" ? <Check size={13} aria-hidden="true" /> : state === "failed" ? <X size={13} aria-hidden="true" /> : null}
                    {state === "reference" ? "" : state}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// The explorer.
// ---------------------------------------------------------------------------
export default function ArchitectureExplorer({
  run,
  session,
  catalog,
  catalogError,
  connection,
  audit,
  auditBusy,
  onVerifyAudit,
  onStartCase,
  notice,
}: {
  run: Run | null;
  session: VisitorSession | null;
  catalog: ScenarioCatalog | null;
  catalogError: Error | null;
  connection: Connection;
  audit: Audit | null;
  auditBusy: boolean;
  onVerifyAudit: () => void;
  onStartCase: () => void;
  notice?: ReactNode;
}) {
  const [lensId, setLensId] = useState<LensId>(lensFromUrl);
  const [choice, setChoice] = useState<Deployment | null>(null);
  const [selections, setSelections] = useState<Partial<Record<LensId, Selection>>>({});
  const [walk, setWalk] = useState<Walk | null>(null);
  const [follow, setFollow] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [fit, setFit] = useState({ width: 1, all: 1 });
  const [motion, setMotion] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const viewport = useRef<HTMLDivElement>(null);
  const manualZoom = useRef(false);
  const pan = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const announce = useRef<HTMLDivElement>(null);

  const lens = lensById(lensId);
  const deployment: Deployment = choice ?? (session?.public_mode ? "public" : "local");
  const context: LiveContext = {
    run,
    session,
    catalog,
    catalogError,
    audit: audit && run ? audit : null,
    connection,
    origin: window.location.origin,
  };
  const liveRun = Boolean(run) && connection === "connected" && !terminal(run);
  const steps = lens.kind === "graph" ? visibleIn(lens.steps, deployment) : [];
  const messageCount = lens.kind === "sequence" ? sequenceMessageCount(lens) : 0;
  const chainLength = lens.kind === "chain" ? chainBlocks(lens, context.audit).blocks.length : 0;
  const walkLength = lens.kind === "graph" ? steps.length : lens.kind === "sequence" ? messageCount : chainLength;
  const walking = walk?.lens === lensId ? walk : null;
  const current = currentStage(run);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("lens", lensId);
    window.history.replaceState(window.history.state, "", url);
  }, [lensId]);
  useEffect(
    () => () => {
      const url = new URL(window.location.href);
      url.searchParams.delete("lens");
      window.history.replaceState(window.history.state, "", url);
    },
    [],
  );
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const changed = () => setMotion(!media.matches);
    media.addEventListener("change", changed);
    return () => media.removeEventListener("change", changed);
  }, []);

  // Fit the graph to the canvas width; narrow screens keep text legible and pan.
  useEffect(() => {
    const element = viewport.current;
    if (!element || lens.kind !== "graph") return;
    const measure = () => {
      const rect = element.getBoundingClientRect();
      const width = Math.min(1, (rect.width - 24) / lens.width);
      const all = Math.min(width, (rect.height - 24) / lens.height);
      setFit({ width, all });
      if (!manualZoom.current) setZoom(rect.width < 620 ? 0.62 : width);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [lens]);
  useEffect(() => {
    manualZoom.current = false;
    viewport.current?.scrollTo({ left: 0, top: 0 });
  }, [lensId]);

  useEffect(() => {
    if (!walking?.playing) return;
    const timer = window.setTimeout(() => {
      setWalk((previous) => {
        if (!previous) return null;
        const next = previous.index + 1;
        return next >= walkLength
          ? { ...previous, playing: false }
          : { ...previous, index: next, inspect: undefined };
      });
    }, WALK_DELAY[lens.kind]);
    return () => window.clearTimeout(timer);
  }, [walking, walkLength, lens.kind]);

  // What the inspector shows: an explicit inspection, the walkthrough, the live
  // run's current component, or the visitor's last selection on this lens.
  const followSelection = ((): Selection | undefined => {
    if (!run || !follow || !current) return undefined;
    if (lens.kind === "graph") {
      const id = lens.focus[current];
      return id && visibleIn(lens.nodes, deployment).some((node) => node.id === id)
        ? { kind: "node", id }
        : undefined;
    }
    if (lens.kind === "sequence") return { kind: "band", id: current };
    return undefined;
  })();
  const walkSelection = ((): Selection | undefined => {
    if (!walking) return undefined;
    if (walking.inspect) return walking.inspect;
    if (lens.kind === "graph") return { kind: "step", id: String(walking.index) };
    if (lens.kind === "sequence") return { kind: "message", id: String(walking.index + 1) };
    const block = chainBlocks(lens, context.audit).blocks[walking.index];
    return block ? { kind: "entry", id: block.id } : undefined;
  })();
  const selection = walkSelection ?? followSelection ?? selections[lensId];
  const highlight =
    lens.kind !== "graph"
      ? undefined
      : walking
        ? steps[walking.index]
        : selection?.kind === "step"
          ? steps[Number(selection.id)]
          : undefined;

  // Persisted stages that are processing right now animate their connections.
  const flowing = useMemo(() => {
    const ids = new Set<string>();
    if (lens.kind !== "graph" || !run || connection !== "connected") return ids;
    for (const edge of lens.edges)
      if (edge.stages?.some((stage) => stageOf(run, stage)?.status === "processing"))
        ids.add(edge.id);
    return ids;
  }, [lens, run, connection]);

  const stepNumbers = useMemo(() => {
    const numbers = new Map<string, number[]>();
    steps.forEach((step, index) => {
      if (step.anchor) numbers.set(step.anchor, [...(numbers.get(step.anchor) ?? []), index + 1]);
    });
    return numbers;
  }, [steps]);

  const reveal = (id: string) => {
    if (lens.kind !== "graph") return;
    const node = lens.nodes.find((item) => item.id === id);
    const element = viewport.current;
    if (!node || !element) return;
    element.scrollTo({
      left: Math.max(0, node.x * zoom - (element.clientWidth - node.w * zoom) / 2),
      top: Math.max(0, node.y * zoom - (element.clientHeight - node.h * zoom) / 2),
      behavior: "instant",
    });
  };
  const revealMessage = (number: number) => {
    const element = viewport.current;
    if (!element || lens.kind !== "sequence") return;
    const row = sequenceRows(lens).rows.find((item) => item.kind === "message" && item.number === number);
    if (!row) return;
    const top = SEQ_HEADER + row.y;
    if (top < element.scrollTop + SEQ_HEADER + 8 || top > element.scrollTop + element.clientHeight - 60)
      element.scrollTo({ top: Math.max(0, top - element.clientHeight / 2), behavior: "instant" });
  };
  const revealEntry = (index: number) => {
    const element = viewport.current;
    // The first list item is the genesis marker.
    const target = element?.querySelectorAll<HTMLElement>(".arch-blocks > li")[index + 1];
    if (!element || !target) return;
    const top = target.getBoundingClientRect().top - element.getBoundingClientRect().top + element.scrollTop;
    if (top < element.scrollTop || top > element.scrollTop + element.clientHeight - 60)
      element.scrollTo({ top: Math.max(0, top - element.clientHeight / 2), behavior: "instant" });
  };
  useEffect(() => {
    if (walking && lens.kind === "chain" && !walking.inspect) revealEntry(walking.index);
    if (walking && lens.kind === "graph") {
      const step = steps[walking.index];
      if (step?.nodes[0] && !walking.inspect) reveal(step.anchor && lens.nodes.some((node) => node.id === step.anchor) ? step.anchor : step.nodes[0]);
    }
    if (walking && lens.kind === "sequence" && !walking.inspect) revealMessage(walking.index + 1);
    if (walking && announce.current)
      announce.current.textContent = `Walkthrough step ${walking.index + 1} of ${walkLength}.`;
  }, [walking?.index, walking?.lens]);
  useEffect(() => {
    if (!walking && followSelection?.kind === "node") reveal(followSelection.id);
  }, [followSelection?.id, zoom]);

  const select = (next: Selection) => {
    setFollow(false);
    if (walking) setWalk({ ...walking, playing: false, inspect: next });
    setSelections((previous) => ({ ...previous, [lensId]: next }));
    if (next.kind === "node") reveal(next.id);
  };
  const startWalk = () => {
    setFollow(false);
    setWalk({ lens: lensId, index: 0, playing: motion });
  };
  const changeLens = (id: LensId) => {
    setLensId(id);
    setWalk(null);
  };
  const updateZoom = (value: number) => {
    manualZoom.current = true;
    setZoom(Math.max(0.3, Math.min(1.4, Math.round(value * 100) / 100)));
  };

  const indicator = !run
    ? { tone: "is-reference", label: "Reference model · no run open" }
    : connection === "disconnected"
      ? { tone: "is-disconnected", label: "Connection interrupted" }
      : connection === "loading"
        ? { tone: "is-disconnected", label: "Connecting to your run" }
        : terminal(run)
          ? { tone: "is-recorded", label: "Persisted record · this run" }
          : { tone: "is-live", label: "Live · following this run" };

  return (
    <section className="arch-explorer" data-testid="architecture-explorer" aria-label="Architecture explorer">
      <div className="arch-heading">
        <div>
          <p className="eyebrow">
            {session
              ? session.public_mode
                ? "PUBLIC PREVIEW · PRIVATE SERVICES"
                : "LOCAL DOCKER TOPOLOGY"
              : "SERVICE TOPOLOGY"}
          </p>
          <h2>Every component, connection, and boundary.</h2>
          <p>
            Seven views of one system, drawn from its code and configuration. With a run
            open, they follow the backend's persisted records; without one, they show the
            reference design and an illustrative walkthrough.
          </p>
        </div>
        <div className="arch-heading-side">
          <span className={`arch-indicator ${indicator.tone}`} data-testid="arch-indicator">
            <span aria-hidden="true" />
            {indicator.label}
          </span>
          {!run && (
            <button type="button" className="arch-link-button" onClick={onStartCase}>
              Start a case to watch it live
              <ArrowRight size={14} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className="arch-environments" aria-label="Deployments">
        <Environment
          icon={Laptop}
          title="Local Docker stack"
          text="make demo-up → http://localhost:3000. Six containers whose ports bind to loopback only; nothing is reachable from other machines."
          status={session && !session.public_mode ? "Serving this page" : "For developers"}
          current={Boolean(session && !session.public_mode)}
        />
        <Environment
          icon={Globe}
          title="Mac-hosted preview"
          text="Cloudflare named tunnel → 127.0.0.1:3100 on the operator's Mac. Seven containers, including an operator-only traffic dashboard."
          status={session?.public_mode ? "Serving this page" : "Operator-managed"}
          current={Boolean(session?.public_mode)}
        />
        <div className="arch-environment is-planned">
          <span className="arch-environment-icon">
            <Cloud size={18} aria-hidden="true" />
          </span>
          <div>
            <div className="arch-environment-title">
              <strong>Google Cloud</strong>
              <span className="badge">Planned</span>
            </div>
            <p>
              No provisioned infrastructure, endpoint, or passing cloud journey. It first needs
              reproducible private infrastructure, storage, secrets and TLS, correlated
              telemetry with spending controls, and full-journey verification.
            </p>
          </div>
        </div>
      </div>
      {notice}

      <ul className="arch-glance" aria-label="System at a glance">
        {atAGlance.map((item) => (
          <li key={item.label}>
            <strong>{item.value}</strong>
            <span>{item.label}</span>
          </li>
        ))}
      </ul>

      <div className="arch-wide">
        <div className="arch-lens-tabs" role="tablist" aria-label="Architecture views">
          {lenses.map((item) => (
            <button
              type="button"
              key={item.id}
              id={`arch-tab-${item.id}`}
              role="tab"
              aria-selected={item.id === lensId}
              aria-controls="arch-lens-panel"
              tabIndex={item.id === lensId ? 0 : -1}
              data-testid={`arch-lens-${item.id}`}
              className={item.id === lensId ? "is-active" : ""}
              onClick={() => changeLens(item.id)}
              onKeyDown={(event: KeyboardEvent<HTMLButtonElement>) => {
                const index = lensIds.indexOf(lensId);
                const next =
                  event.key === "ArrowRight"
                    ? (index + 1) % lensIds.length
                    : event.key === "ArrowLeft"
                      ? (index - 1 + lensIds.length) % lensIds.length
                      : event.key === "Home"
                        ? 0
                        : event.key === "End"
                          ? lensIds.length - 1
                          : -1;
                if (next < 0) return;
                event.preventDefault();
                changeLens(lensIds[next]);
                document.getElementById(`arch-tab-${lensIds[next]}`)?.focus();
              }}
            >
              <item.icon size={15} aria-hidden="true" />
              {item.tab}
            </button>
          ))}
        </div>

        <div
          className="arch-workbench"
          id="arch-lens-panel"
          role="tabpanel"
          aria-labelledby={`arch-tab-${lensId}`}
        >
          <div className="arch-canvas-panel">
            <div className="arch-toolbar">
              <div className="arch-toolbar-title">
                <lens.icon size={16} aria-hidden="true" />
                <div>
                  <strong>{lens.title}</strong>
                  <span>{lens.summary}</span>
                </div>
              </div>
              <div className="arch-toolbar-actions">
                {lens.kind === "graph" && lens.deployable && (
                  <div className="arch-segmented" role="group" aria-label="Deployment shown in the diagram">
                    {(["local", "public"] as const).map((item) => (
                      <button
                        type="button"
                        key={item}
                        data-testid={`arch-deployment-${item}`}
                        aria-pressed={deployment === item}
                        onClick={() => {
                          setChoice(item);
                          setSelections((previous) => ({ ...previous, [lensId]: undefined }));
                          setWalk(null);
                        }}
                      >
                        {item === "local" ? "Local stack" : "Mac preview"}
                      </button>
                    ))}
                  </div>
                )}
                {run && lens.kind !== "chain" && (
                  <button
                    type="button"
                    className="arch-button subtle"
                    aria-pressed={follow && !walking}
                    disabled={Boolean(walking)}
                    onClick={() => setFollow(!follow)}
                    title="Keep the inspector on the component the run is using"
                  >
                    {follow && !walking ? <Check size={13} aria-hidden="true" /> : <Activity size={13} aria-hidden="true" />}
                    Follow run
                  </button>
                )}
                <div className="arch-walk-controls" role="group" aria-label="Walkthrough">
                  {walking ? (
                    <>
                      <IconButton
                        label="Previous walkthrough step"
                        disabled={walking.index === 0}
                        onClick={() => setWalk({ ...walking, index: walking.index - 1, playing: false, inspect: undefined })}
                      >
                        <ArrowLeft size={14} aria-hidden="true" />
                      </IconButton>
                      <button
                        type="button"
                        className="arch-button primary"
                        onClick={() =>
                          setWalk({
                            ...walking,
                            inspect: undefined,
                            index: walking.index >= walkLength - 1 ? 0 : walking.index,
                            playing: !walking.playing,
                          })
                        }
                      >
                        {walking.playing ? <Pause size={13} aria-hidden="true" /> : <Play size={13} aria-hidden="true" />}
                        {walking.playing ? "Pause" : "Play"}
                      </button>
                      <IconButton
                        label="Next walkthrough step"
                        disabled={walking.index >= walkLength - 1}
                        onClick={() => setWalk({ ...walking, index: walking.index + 1, playing: false, inspect: undefined })}
                      >
                        <ArrowRight size={14} aria-hidden="true" />
                      </IconButton>
                      <span className="arch-walk-position" data-testid="arch-walk-position">
                        {walking.index + 1} / {walkLength}
                      </span>
                      <button type="button" className="arch-button subtle" onClick={() => setWalk(null)}>
                        <X size={13} aria-hidden="true" />
                        Exit
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="arch-button primary"
                      disabled={!walkLength}
                      onClick={startWalk}
                    >
                      <Play size={13} aria-hidden="true" />
                      Walk through
                    </button>
                  )}
                </div>
                {lens.kind === "graph" && (
                  <div className="arch-zoom" role="group" aria-label="Zoom">
                    <IconButton label="Zoom out" onClick={() => updateZoom(zoom - 0.1)} disabled={zoom <= 0.3}>
                      <span aria-hidden="true">−</span>
                    </IconButton>
                    <span className="arch-zoom-value">{Math.round(zoom * 100)}%</span>
                    <IconButton label="Zoom in" onClick={() => updateZoom(zoom + 0.1)} disabled={zoom >= 1.4}>
                      <span aria-hidden="true">+</span>
                    </IconButton>
                    <IconButton
                      label="Fit the whole diagram"
                      onClick={() => {
                        manualZoom.current = true;
                        setZoom(Math.max(0.3, fit.all));
                        viewport.current?.scrollTo({ left: 0, top: 0 });
                      }}
                    >
                      <Maximize2 size={13} aria-hidden="true" />
                    </IconButton>
                  </div>
                )}
              </div>
            </div>
            <div
              className={`arch-viewport is-${lens.kind}`}
              ref={viewport}
              tabIndex={0}
              role="region"
              aria-label={`${lens.tab} diagram. Scroll or drag to pan; use Tab and the arrow keys to move between components.`}
              onPointerDown={(event) => {
                if (event.pointerType !== "mouse" || event.button !== 0 || (event.target as Element).closest("button"))
                  return;
                pan.current = {
                  x: event.clientX,
                  y: event.clientY,
                  left: event.currentTarget.scrollLeft,
                  top: event.currentTarget.scrollTop,
                };
                event.currentTarget.setPointerCapture(event.pointerId);
              }}
              onPointerMove={(event) => {
                if (!pan.current) return;
                event.currentTarget.scrollLeft = pan.current.left - (event.clientX - pan.current.x);
                event.currentTarget.scrollTop = pan.current.top - (event.clientY - pan.current.y);
              }}
              onPointerUp={(event) => {
                pan.current = null;
                if (event.currentTarget.hasPointerCapture(event.pointerId))
                  event.currentTarget.releasePointerCapture(event.pointerId);
              }}
              onPointerCancel={() => {
                pan.current = null;
              }}
            >
              {lens.kind === "graph" && (
                <div className="arch-scene-space" style={{ width: lens.width * zoom, height: lens.height * zoom }}>
                  <div className="arch-scene-scale" style={{ transform: `scale(${zoom})` }}>
                    <GraphCanvas
                      lens={lens}
                      deployment={deployment}
                      context={context}
                      selection={selection}
                      highlight={highlight}
                      flowing={flowing}
                      motion={motion}
                      paused={Boolean(walking && !walking.playing)}
                      stepNumbers={stepNumbers}
                      onSelect={select}
                      focusNode={(id) =>
                        viewport.current
                          ?.querySelector<HTMLButtonElement>(`[data-testid="arch-node-${id}"]`)
                          ?.focus({ preventScroll: true })
                      }
                    />
                  </div>
                </div>
              )}
              {lens.kind === "sequence" && (
                <SequenceCanvas
                  lens={lens}
                  context={context}
                  selection={selection}
                  walkNumber={walking ? walking.index + 1 : undefined}
                  motion={motion}
                  onSelect={select}
                />
              )}
              {lens.kind === "chain" && (
                <ChainCanvas
                  lens={lens}
                  context={context}
                  auditBusy={auditBusy}
                  onVerify={onVerifyAudit}
                  selection={selection}
                  walkIndex={walking?.index}
                  onSelect={select}
                />
              )}
            </div>
            <Legend lens={lens} live={Boolean(run)} />
          </div>
          <Inspector
            lens={lens}
            deployment={deployment}
            context={context}
            selection={selection}
            steps={steps}
            walkLength={walkLength}
            liveRun={liveRun}
            onSelect={select}
            onStartWalk={startWalk}
          />
        </div>

        <LensNotes
          lens={lens}
          steps={steps}
          context={context}
          selection={selection}
          walkingIndex={walking?.index}
          onStep={(index) => {
            setFollow(false);
            setWalk({ lens: lensId, index, playing: false });
          }}
          onBand={(id) => select({ kind: "band", id })}
        />
      </div>
      <p className="arch-footnote">
        <Info size={13} aria-hidden="true" />
        Diagrams are drawn from the repository's Compose files, gateway configuration, Java and
        Python services, and database migrations. Highlighting follows persisted backend records;
        animation marks activity, not individual network packets. The walkthrough is illustrative.
      </p>
      <div className="sr-only" aria-live="polite" ref={announce} />
    </section>
  );
}

function Environment({
  icon: Icon,
  title,
  text: body,
  status,
  current,
}: {
  icon: LucideIcon;
  title: string;
  text: string;
  status: string;
  current: boolean;
}) {
  return (
    <div className={`arch-environment ${current ? "is-current" : ""}`}>
      <span className="arch-environment-icon">
        <Icon size={18} aria-hidden="true" />
      </span>
      <div>
        <div className="arch-environment-title">
          <strong>{title}</strong>
          <span className={`arch-environment-status ${current ? "is-current" : ""}`}>
            {current && <span aria-hidden="true" />}
            {status}
          </span>
        </div>
        <p>{body}</p>
      </div>
    </div>
  );
}

function Legend({ lens, live }: { lens: Lens; live: boolean }) {
  return (
    <div className="arch-legend">
      {lens.kind === "graph" &&
        (["request", "event", "data", "control"] as const).map((kind) => (
          <span className="arch-legend-item" key={kind}>
            <svg width="26" height="8" aria-hidden="true">
              <line className={`arch-legend-line is-${kind}`} x1="1" y1="4" x2="25" y2="4" />
            </svg>
            {edgeKindLabels[kind]}
          </span>
        ))}
      {lens.kind === "graph" && (
        <span className="arch-legend-item">
          <i className="arch-legend-boundary" aria-hidden="true" />
          Trust or network boundary
        </span>
      )}
      {lens.kind === "sequence" &&
        [
          ["call", "Call"],
          ["return", "Response"],
          ["async", "Kafka event"],
        ].map(([kind, label]) => (
          <span className="arch-legend-item" key={kind}>
            <svg width="26" height="8" aria-hidden="true">
              <line className={`arch-legend-line is-${kind}`} x1="1" y1="4" x2="25" y2="4" />
            </svg>
            {label}
          </span>
        ))}
      {lens.kind === "chain" && (
        <span className="arch-legend-item">
          <Link2 size={12} aria-hidden="true" />
          Each row is linked to its parent by SHA-256
        </span>
      )}
      {live &&
        (
          [
            ["recorded", "Recorded"],
            ["processing", "Processing"],
            ["waiting", "Waiting"],
            ["failed", "Failed or blocked"],
          ] as const
        ).map(([state, label]) => (
          <span className="arch-legend-item" key={state}>
            <i className={`arch-legend-dot is-${state}`} aria-hidden="true" />
            {label}
          </span>
        ))}
      <span className="arch-legend-hint">Drag to pan · select to inspect</span>
    </div>
  );
}

function Inspector({
  lens,
  deployment,
  context,
  selection,
  steps,
  walkLength,
  liveRun,
  onSelect,
  onStartWalk,
}: {
  lens: Lens;
  deployment: Deployment;
  context: LiveContext;
  selection?: Selection;
  steps: ArchStep[];
  walkLength: number;
  liveRun: boolean;
  onSelect: (selection: Selection) => void;
  onStartWalk: () => void;
}) {
  const { run } = context;
  const nodeTitle = (id: string) =>
    lens.kind === "graph"
      ? (visibleIn(lens.nodes, deployment).find((node) => node.id === id)?.title ?? id).replace("​", "")
      : id;
  let eyebrow = "OVERVIEW";
  let title = lens.tab;
  let subtitle = "";
  let Icon: LucideIcon = lens.icon;
  let tone = "overview";
  let status: { state: string; label: string } | undefined;
  let body: ReactNode = (
    <>
      <p className="arch-inspector-summary">{lens.summary}</p>
      <p className="arch-inspector-reading">{lens.reading}</p>
      <button type="button" className="arch-button primary arch-inspector-cta" onClick={onStartWalk} disabled={!walkLength}>
        <Play size={13} aria-hidden="true" />
        Walk through this view
      </button>
      {run && (
        <p className="arch-inspector-note">
          {liveRun
            ? "This view is following your run. Components light up as the backend records each stage."
            : "This view shows your run's persisted record."}
        </p>
      )}
    </>
  );

  if (lens.kind === "graph" && selection?.kind === "node") {
    const node = visibleIn(lens.nodes, deployment).find((item) => item.id === selection.id);
    if (node) {
      const view = nodeView(lens, node, context);
      eyebrow = `${lens.tab.toUpperCase()} · ${toneLabels[node.tone].toUpperCase()}`;
      title = node.title.replace("​", "");
      subtitle = node.tech;
      Icon = node.icon;
      tone = node.tone;
      if (run && view.pill) status = { state: view.state, label: view.pill };
      const edges = visibleIn(lens.edges, deployment).filter((edge) => edge.from === node.id || edge.to === node.id);
      body = (
        <>
          <DetailBody detail={node.detail} live={liveFacts(node.live, context)} />
          {node.columns && (
            <section>
              <h4>Columns</h4>
              <Facts facts={node.columns.map((column) => [`${column.key ? `${column.key} · ` : ""}${column.name}`, column.type])} />
            </section>
          )}
          {edges.length > 0 && (
            <section>
              <h4>Connections</h4>
              <ul className="arch-related">
                {edges.map((edge) => (
                  <li key={edge.id}>
                    <button type="button" onClick={() => onSelect({ kind: "edge", id: edge.id })}>
                      <span>{edge.from === node.id ? "→" : "←"}</span>
                      {nodeTitle(edge.from === node.id ? edge.to : edge.from)}
                      {edge.label && <small>{edge.label}</small>}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      );
    }
  }
  if (lens.kind === "graph" && selection?.kind === "edge") {
    const edge = visibleIn(lens.edges, deployment).find((item) => item.id === selection.id);
    if (edge) {
      eyebrow = `CONNECTION · ${edgeKindLabels[edge.kind].toUpperCase()}`;
      title = edge.label ?? `${nodeTitle(edge.from)} → ${nodeTitle(edge.to)}`;
      subtitle = `${nodeTitle(edge.from)} ${edge.twoWay ? "↔" : "→"} ${nodeTitle(edge.to)}`;
      Icon = Link2;
      tone = edge.kind;
      if (run && edge.stages?.length) {
        const state = stageState(run, edge.stages);
        status = { state: state.state, label: stateLabel(state.state, state.recorded, state.total) };
      }
      body = (
        <>
          <DetailBody detail={edge.detail} />
          {edge.stages && (
            <section>
              <h4>Used by stages</h4>
              <p className="arch-inline-list">{edge.stages.map(stageTitle).join(" · ")}</p>
            </section>
          )}
          <section>
            <h4>Endpoints</h4>
            <ul className="arch-related">
              {[edge.from, edge.to].map((id) => (
                <li key={id}>
                  <button type="button" onClick={() => onSelect({ kind: "node", id })}>
                    <span>{id === edge.from ? "from" : "to"}</span>
                    {nodeTitle(id)}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </>
      );
    }
  }
  if (lens.kind === "graph" && selection?.kind === "step") {
    const index = Number(selection.id);
    const step = steps[index];
    if (step) {
      eyebrow = `${lens.stepsTitle.toUpperCase()} · STEP ${index + 1} OF ${steps.length}`;
      title = step.title;
      subtitle = step.stages?.map(stageTitle).join(" · ") ?? "";
      Icon = lens.icon;
      body = (
        <>
          <p className="arch-inspector-summary">{step.text}</p>
          {run && step.stages && (
            <section className="arch-live-evidence">
              <h4>
                <span className="arch-live-dot" aria-hidden="true" />
                This run
              </h4>
              <Facts
                facts={step.stages.map((id) => {
                  const stage = stageOf(run, id);
                  return [stageTitle(id), stage ? `${stage.status}${typeof stage.duration_ms === "number" ? ` · ${duration(stage.duration_ms)}` : ""}` : "not recorded"];
                })}
              />
            </section>
          )}
          <section>
            <h4>Components in this step</h4>
            <ul className="arch-related">
              {step.nodes.map((id) => (
                <li key={id}>
                  <button type="button" onClick={() => onSelect({ kind: "node", id })}>
                    <span>•</span>
                    {nodeTitle(id)}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </>
      );
    }
  }
  if (lens.kind === "sequence") {
    const name = (id: string) => lens.participants.find((participant) => participant.id === id)?.title ?? id;
    if (selection?.kind === "participant") {
      const participant = lens.participants.find((item) => item.id === selection.id);
      if (participant) {
        eyebrow = "PARTICIPANT";
        title = participant.title;
        subtitle = participant.tech;
        Icon = participant.icon;
        tone = participant.tone;
        body = <DetailBody detail={participant.detail} />;
      }
    }
    if (selection?.kind === "message") {
      const rows = sequenceRows(lens).rows;
      const row = rows.find((item) => item.kind === "message" && String(item.number) === selection.id);
      if (row && row.kind === "message") {
        const { message, band } = row;
        eyebrow = `MESSAGE ${row.number} OF ${sequenceMessageCount(lens)} · ${band.title.toUpperCase()}`;
        title = message.label;
        subtitle = message.kind === "self" ? `${name(message.from)} · internal step` : `${name(message.from)} → ${name(message.to)} · ${message.kind === "return" ? "response" : message.kind === "async" ? "Kafka event" : "call"}`;
        Icon = lens.participants.find((participant) => participant.id === message.from)?.icon ?? lens.icon;
        tone = lens.participants.find((participant) => participant.id === message.from)?.tone ?? "overview";
        const state = bandState(band, context);
        if (run && state !== "idle") status = { state, label: `${stageTitle(band.id)}: ${state}` };
        body = <DetailBody detail={message.detail} />;
      }
    }
    if (selection?.kind === "band") {
      const band = lens.bands.find((item) => item.id === selection.id);
      if (band) {
        const stage = stageOf(run, band.id);
        eyebrow = band.id === "session" || band.id === "polling" ? "INTERACTION" : "PERSISTED STAGE";
        title = band.title;
        subtitle = band.caption;
        Icon = lens.icon;
        const state = bandState(band, context);
        if (run && state !== "idle") status = { state, label: state };
        body = (
          <>
            <p className="arch-inspector-summary">
              {band.messages.length} message{band.messages.length === 1 ? "" : "s"}:{" "}
              {band.messages.map((message) => message.label).join(" → ")}.
            </p>
            {stage && (
              <section className="arch-live-evidence">
                <h4>
                  <span className="arch-live-dot" aria-hidden="true" />
                  Recorded for this run
                </h4>
                <Facts
                  facts={[
                    ["Status", stage.status],
                    ["Producer", text(stage.producer)],
                    ["Attempt", text(stage.attempt)],
                    ["Duration", duration(stage.duration_ms)],
                    ["Started", date(stage.started_at)],
                    ["Completed", date(stage.completed_at)],
                    ...(stage.error ? ([["Error", text(object(stage.error).code ?? stage.error)]] as Fact[]) : []),
                  ]}
                />
              </section>
            )}
          </>
        );
      }
    }
  }
  if (lens.kind === "chain") {
    if (selection?.kind === "entry") {
      const block = chainBlocks(lens, context.audit).blocks.find((item) => item.id === selection.id);
      if (block) {
        eyebrow = `JOURNAL ENTRY #${block.sequence}`;
        title = block.type;
        subtitle = block.producer;
        Icon = Fingerprint;
        tone = "data";
        body = block.hash ? (
          <>
            <Facts
              facts={[
                ["Occurred", date(block.at)],
                ["Journal event", block.id],
                ["parent_hash", block.parent ?? ""],
                ["current_hash", block.hash],
              ]}
              className="is-hashes"
            />
            <section>
              <h4>Hashed payload</h4>
              <pre className="arch-payload" tabIndex={0} aria-label="Hashed journal payload JSON">
                {JSON.stringify(block.payload, null, 2)}
              </pre>
            </section>
          </>
        ) : (
          <>
            <p className="arch-inspector-summary">
              {block.type.endsWith("processing")
                ? "Written when the stage starts: status processing, an incremented attempt and started_at."
                : "Written when the stage commits its evidence, output digest and duration."}{" "}
              The payload records the run, source event, journal event ID, stage, status, case
              version, timestamp, producer and evidence.
            </p>
            <p className="arch-inspector-note">
              Open a run and load its chain to see real rows and hashes.
            </p>
          </>
        );
      }
    }
    if (selection?.kind === "check") {
      const check = lens.checks.find((item) => item.id === selection.id);
      if (check) {
        eyebrow = "VERIFICATION CHECK";
        title = check.title;
        Icon = ShieldCheck;
        tone = "security";
        body = (
          <>
            <p className="arch-inspector-summary">{check.text}</p>
            <section>
              <h4>Failure codes</h4>
              <ul className="arch-source">
                {check.codes.map((code) => (
                  <li key={code}>
                    <code>{code}</code>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h4>When verification runs</h4>
              <ul className="arch-bullets">
                {lens.when.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          </>
        );
      }
    }
  }

  return (
    <section className="arch-inspector" data-testid="arch-inspector" aria-label="Selected item details" tabIndex={0}>
      <div className="arch-inspector-heading">
        <span className={`arch-inspector-icon tone-${tone}`}>
          <Icon size={18} aria-hidden="true" />
        </span>
        <div>
          <p className="arch-inspector-eyebrow">{eyebrow}</p>
          <h3>{title}</h3>
          {subtitle && <span>{subtitle}</span>}
        </div>
      </div>
      {status && (
        <div className={`arch-status is-${status.state}`} data-testid="arch-inspector-status">
          <span aria-hidden="true" />
          {status.label}
        </div>
      )}
      {body}
    </section>
  );
}

function LensNotes({
  lens,
  steps,
  context,
  selection,
  walkingIndex,
  onStep,
  onBand,
}: {
  lens: Lens;
  steps: ArchStep[];
  context: LiveContext;
  selection?: Selection;
  walkingIndex?: number;
  onStep: (index: number) => void;
  onBand: (id: string) => void;
}) {
  const { run } = context;
  if (lens.kind === "graph")
    return (
      <section className="arch-notes" aria-label={lens.stepsTitle}>
        <div className="arch-notes-heading">
          <p className="arch-inspector-eyebrow">{lens.stepsTitle.toUpperCase()}</p>
          <h3>{lens.reading}</h3>
        </div>
        <ol className="arch-steps">
          {steps.map((step, index) => {
            const selected =
              (selection?.kind === "step" && Number(selection.id) === index) || walkingIndex === index;
            const state = run && step.stages ? stageState(run, step.stages) : undefined;
            return (
              <li key={`${step.title}-${index}`}>
                <button
                  type="button"
                  data-testid={`arch-step-${index + 1}`}
                  className={`arch-step ${selected ? "is-selected" : ""}`}
                  aria-pressed={selected}
                  onClick={() => onStep(index)}
                >
                  <span className="arch-step-number">{index + 1}</span>
                  <span className="arch-step-body">
                    <strong>{step.title}</strong>
                    <span>{step.text}</span>
                  </span>
                  {state && (
                    <span className={`arch-step-state is-${state.state}`}>
                      {stateLabel(state.state, state.recorded, state.total)}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ol>
      </section>
    );
  if (lens.kind === "sequence")
    return (
      <section className="arch-notes" aria-label="Stages">
        <div className="arch-notes-heading">
          <p className="arch-inspector-eyebrow">PERSISTED STAGES</p>
          <h3>{lens.reading}</h3>
        </div>
        <ol className="arch-stage-strip">
          {lens.bands
            .filter((band) => band.id !== "session" && band.id !== "polling")
            .map((band, index) => {
              const stage = stageOf(run, band.id);
              const state = bandState(band, context);
              return (
                <li key={band.id}>
                  <button
                    type="button"
                    className={`arch-stage-chip is-${state} ${selection?.kind === "band" && selection.id === band.id ? "is-selected" : ""}`}
                    onClick={() => onBand(band.id)}
                  >
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{band.title}</strong>
                    <small>{stage ? `${stage.status}${typeof stage.duration_ms === "number" ? ` · ${duration(stage.duration_ms)}` : ""}` : band.caption}</small>
                  </button>
                </li>
              );
            })}
        </ol>
      </section>
    );
  return (
    <section className="arch-notes is-chain" aria-label="Verification scope">
      <div>
        <p className="arch-inspector-eyebrow">WHEN VERIFICATION RUNS</p>
        <ul className="arch-bullets">
          {lens.when.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div>
        <p className="arch-inspector-eyebrow">WHAT IT DOES NOT CLAIM</p>
        <ul className="arch-bullets">
          {lens.scope.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
