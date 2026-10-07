import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Check,
  Clock3,
  Code2,
  Copy,
  Fingerprint,
  Info,
  Pause,
  Play,
  RotateCcw,
  type LucideIcon,
} from "./icons";
import { date, duration, words, type Run } from "./api";
import {
  flowEdges,
  flowSteps,
  payloadForStep,
  recordedSteps,
} from "./flow-model";
import "./transaction-flow.css";

type Replay = {
  snapshot: Run;
  index: number;
  playing: boolean;
  inspectedId?: string;
};
type PayloadTab = "input" | "output";
const SCENE_WIDTH = 900;
const SCENE_HEIGHT = 704;
const NODE_WIDTH = 180;
const NODE_HEIGHT = 112;
const positions = [
  [46, 46],
  [360, 46],
  [674, 46],
  [674, 212],
  [360, 212],
  [46, 212],
  [46, 378],
  [360, 378],
  [674, 378],
  [674, 544],
  [360, 544],
];

function currentStep(run: Run): string {
  return (
    run.stages.find((stage) => stage.status === "processing")?.stage ??
    run.stages.find(
      (stage) => stage.status === "failed" || stage.status === "blocked",
    )?.stage ??
    (run.status === "AWAITING_REVIEW" ? "decision" : undefined) ??
    recordedSteps(run).at(-1)?.stage ??
    "submission"
  );
}

function edgeGeometry(source: string, target: string) {
  const [sx, sy] = positions[flowSteps.findIndex((step) => step.id === source)];
  const [tx, ty] = positions[flowSteps.findIndex((step) => step.id === target)];
  if (sy === ty) {
    const right = tx > sx;
    const x1 = right ? sx + NODE_WIDTH : sx;
    const x2 = right ? tx : tx + NODE_WIDTH;
    return {
      path: `M ${x1} ${sy + 56} L ${x2} ${ty + 56}`,
      x: (x1 + x2) / 2,
      y: sy + 29,
      vertical: false,
    };
  }
  return {
    path: `M ${sx + 90} ${sy + NODE_HEIGHT} L ${tx + 90} ${ty}`,
    x: sx + 90 + (sx > 400 ? -88 : 88),
    y: (sy + NODE_HEIGHT + ty) / 2 - 10,
    vertical: true,
  };
}

function JsonEvidence({ value }: { value: unknown }) {
  const json = JSON.stringify(value, null, 2) ?? "No recorded evidence";
  const tokens = json.split(
    /("(?:\\.|[^"\\])*"\s*:|"(?:\\.|[^"\\])*"|\b(?:true|false|null)\b|-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)/g,
  );
  return (
    <>
      {tokens.map((part, index) => {
        const className = /^".*:\s*$/.test(part)
          ? "json-key"
          : part.startsWith('"')
            ? "json-string"
            : /^(true|false|null)$/.test(part)
              ? "json-boolean"
              : /^-?\d/.test(part)
                ? "json-number"
                : undefined;
        return className ? (
          <span className={className} key={index}>
            {part}
          </span>
        ) : (
          part
        );
      })}
    </>
  );
}

function SmallButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className="flow-icon-button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

function NodeIcon({ icon: Icon }: { icon: LucideIcon }) {
  return <Icon size={21} aria-hidden="true" />;
}

export default function TransactionFlow({
  run,
  connection,
  onReview,
}: {
  run: Run;
  connection: "loading" | "connected" | "disconnected";
  onReview: () => void;
}) {
  const [selection, setSelection] = useState(() => currentStep(run));
  const [tab, setTab] = useState<PayloadTab>("output");
  const [follow, setFollow] = useState(true);
  const [replay, setReplay] = useState<Replay | null>(null);
  const [speed, setSpeed] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [fitZoom, setFitZoom] = useState(1);
  const [copyState, setCopyState] = useState("");
  const [motion, setMotion] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const viewport = useRef<HTMLDivElement>(null);
  const scene = useRef<HTMLDivElement>(null);
  const hasManualZoom = useRef(false);
  const copyTimer = useRef(0);
  const pan = useRef<{
    x: number;
    y: number;
    left: number;
    top: number;
  } | null>(null);
  const displayRun = replay?.snapshot ?? run;
  const recorded = recordedSteps(displayRun);
  const replayStage = replay ? recorded[replay.index]?.stage : undefined;
  const selectedId =
    replay?.inspectedId ??
    replayStage ??
    (follow ? currentStep(run) : selection);
  const selectedInfo =
    flowSteps.find((step) => step.id === selectedId) ?? flowSteps[0];
  const selectedIndex = flowSteps.indexOf(selectedInfo);
  const selectedStage = displayRun.stages.find(
    (stage) => stage.stage === selectedInfo.id,
  );
  const selectedStatus = selectedStage?.status ?? "waiting";
  const payload = payloadForStep(displayRun, selectedInfo.id, tab);
  const completed = displayRun.stages.filter((stage) =>
    ["completed", "abstained"].includes(stage.status),
  ).length;
  const timings = displayRun.stages.flatMap((stage) =>
    typeof stage.duration_ms === "number" ? [stage.duration_ms] : [],
  );
  const totalDuration = timings.length
    ? timings.reduce((sum, value) => sum + value, 0)
    : undefined;
  const terminal = ["COMPLETED", "EXPIRED", "FAILED"].includes(run.status);
  const activeStep = currentStep(displayRun);
  const latestChanged = replay && run.updated_at !== replay.snapshot.updated_at;

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const resize = new ResizeObserver(([entry]) => {
      const next = Math.min(1, entry.contentRect.width / SCENE_WIDTH);
      setFitZoom(next);
      if (!hasManualZoom.current)
        setZoom(entry.contentRect.width < 600 ? 1 : next);
    });
    resize.observe(element);
    return () => resize.disconnect();
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const changed = () => setMotion(!media.matches);
    media.addEventListener("change", changed);
    return () => media.removeEventListener("change", changed);
  }, []);

  useEffect(() => {
    if (!replay?.playing) return;
    const timer = window.setTimeout(() => {
      setReplay((previous) => {
        if (!previous) return null;
        const next = previous.index + 1;
        return next >= recordedSteps(previous.snapshot).length
          ? { ...previous, playing: false }
          : {
              ...previous,
              inspectedId: undefined,
              index: next,
              playing: next < recordedSteps(previous.snapshot).length - 1,
            };
      });
    }, 1500 / speed);
    return () => window.clearTimeout(timer);
  }, [replay, speed]);

  useEffect(() => {
    setCopyState("");
    window.clearTimeout(copyTimer.current);
    return () => window.clearTimeout(copyTimer.current);
  }, [selectedId, tab]);

  // Keep keyboard focus in the graph; scroll just this viewport, never the page.
  const reveal = (id: string) => {
    const index = flowSteps.findIndex((step) => step.id === id);
    const element = viewport.current;
    if (index < 0 || !element) return;
    const [x, y] = positions[index];
    const left = x * zoom;
    const top = y * zoom;
    element.scrollTo({
      left: Math.max(0, left - (element.clientWidth - NODE_WIDTH * zoom) / 2),
      top: Math.max(0, top - (element.clientHeight - NODE_HEIGHT * zoom) / 2),
      behavior: "instant",
    });
  };
  useEffect(() => {
    if (follow || replay) reveal(selectedId);
  }, [selectedId, follow, replayStage, zoom]);

  const selectStep = (id: string, payloadTab?: PayloadTab) => {
    setSelection(id);
    setFollow(false);
    if (payloadTab) setTab(payloadTab);
    if (replay) {
      const index = recorded.findIndex((stage) => stage.stage === id);
      if (index >= 0)
        setReplay({ ...replay, inspectedId: undefined, index, playing: false });
      else setReplay({ ...replay, inspectedId: id, playing: false });
    }
    reveal(id);
  };
  const startReplay = () => {
    setReplay({
      snapshot: run,
      index: 0,
      playing: motion && recordedSteps(run).length > 1,
    });
    setCopyState("");
  };
  const copyPayload = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setCopyState("Copied");
    } catch {
      setCopyState("Copy unavailable. Select the JSON to copy it.");
    }
    copyTimer.current = window.setTimeout(() => setCopyState(""), 3000);
  };
  const updateZoom = (value: number) => {
    hasManualZoom.current = true;
    setZoom(Math.max(0.35, Math.min(1.5, value)));
  };
  const statusLabel = replay
    ? "Recorded replay"
    : connection === "loading"
      ? "Connecting to backend"
      : connection === "disconnected"
        ? "Connection interrupted"
        : terminal
          ? "Persisted record"
          : "Live backend";

  return (
    <section
      className="transaction-flow"
      data-testid="transaction-flow"
      aria-label="Transaction flow explorer"
    >
      <div className="flow-heading">
        <div>
          <p className="eyebrow accent">ONE REQUEST. EVERY HANDOFF.</p>
          <h2>See the whole story unfold.</h2>
          <p>
            Follow your transaction through Inforsight. Select a component or
            connection to explore its evidence.
          </p>
        </div>
        <div
          className={`flow-live-indicator ${replay || terminal ? "is-recorded" : connection === "connected" ? "is-live" : "is-disconnected"}`}
        >
          <span />
          {statusLabel}
        </div>
      </div>

      <div className="flow-stats">
        <div className="flow-stat">
          <span className="flow-stat-label">
            <Check size={14} /> Recorded stages
          </span>
          <strong className="flow-stat-value">
            {completed}
            <small> / {flowSteps.length}</small>
          </strong>
          <span className="flow-stat-detail">
            Completed or explicitly abstained
          </span>
        </div>
        <div className="flow-stat">
          <span className="flow-stat-label">
            <Clock3 size={14} /> Recorded service time
          </span>
          <strong className="flow-stat-value">{duration(totalDuration)}</strong>
          <span className="flow-stat-detail">
            Sum of available stage durations; excludes waiting
          </span>
        </div>
        <div className="flow-stat">
          <span className="flow-stat-label">
            <Activity size={14} />{" "}
            {replay ? "Replay checkpoint" : "Current checkpoint"}
          </span>
          <strong className="flow-stat-value flow-checkpoint-value">
            {
              flowSteps.find((step) => step.id === (replayStage ?? activeStep))
                ?.title
            }
          </strong>
          <span className="flow-stat-detail">
            {replay
              ? `Step ${replay.index + 1} of ${recorded.length} recorded steps`
              : words(run.status)}
          </span>
        </div>
      </div>

      <div className="flow-workbench">
        <div className="flow-canvas-panel">
          <div className="flow-toolbar">
            <div className="flow-toolbar-title">
              <Activity size={16} />
              <strong>Transaction map</strong>
              <span className="flow-toolbar-subtitle">11 checkpoints</span>
            </div>
            <div className="flow-toolbar-actions">
              <button
                className="flow-button subtle"
                aria-pressed={follow && !replay}
                disabled={Boolean(replay)}
                onClick={() => {
                  setFollow(!follow);
                  setSelection(selectedId);
                }}
                title="Keep the inspector on the latest active checkpoint"
              >
                {follow && !replay ? (
                  <Check size={13} />
                ) : (
                  <Activity size={13} />
                )}
                Follow activity
              </button>
              <SmallButton
                label="Zoom out"
                onClick={() => updateZoom(zoom - 0.1)}
                disabled={zoom <= 0.35}
              >
                <span aria-hidden="true">−</span>
              </SmallButton>
              <span className="flow-zoom-value">{Math.round(zoom * 100)}%</span>
              <SmallButton
                label="Zoom in"
                onClick={() => updateZoom(zoom + 0.1)}
                disabled={zoom >= 1.5}
              >
                <span aria-hidden="true">+</span>
              </SmallButton>
              <SmallButton
                label="Fit to view"
                onClick={() => {
                  hasManualZoom.current = false;
                  setZoom(fitZoom);
                  viewport.current?.scrollTo({ left: 0, top: 0 });
                }}
              >
                <RotateCcw size={14} />
              </SmallButton>
            </div>
          </div>
          <div
            className="flow-viewport"
            ref={viewport}
            onPointerDown={(event) => {
              if (
                event.pointerType !== "mouse" ||
                event.button !== 0 ||
                (event.target as Element).closest("button")
              )
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
              event.currentTarget.scrollLeft =
                pan.current.left - (event.clientX - pan.current.x);
              event.currentTarget.scrollTop =
                pan.current.top - (event.clientY - pan.current.y);
            }}
            onPointerUp={(event) => {
              pan.current = null;
              if (event.currentTarget.hasPointerCapture(event.pointerId))
                event.currentTarget.releasePointerCapture(event.pointerId);
            }}
            onPointerCancel={() => {
              pan.current = null;
            }}
            tabIndex={0}
            role="region"
            aria-label="Scrollable transaction map. Use Tab to select components; arrow keys move between components."
          >
            <div
              className="flow-scene-space"
              style={{ width: SCENE_WIDTH * zoom, height: SCENE_HEIGHT * zoom }}
            >
              <div
                className="flow-scene"
                ref={scene}
                style={{
                  width: SCENE_WIDTH,
                  height: SCENE_HEIGHT,
                  transform: `scale(${zoom})`,
                  transformOrigin: "top left",
                }}
              >
                <div className="flow-canvas-caption">
                  <span>
                    {replay ? "RECORDED REPLAY" : "REQUEST LIFECYCLE"}
                  </span>
                  <span>Event → evidence → human decision</span>
                </div>
                <svg
                  className="flow-connections"
                  viewBox={`0 0 ${SCENE_WIDTH} ${SCENE_HEIGHT}`}
                  aria-hidden="true"
                >
                  <defs>
                    <marker
                      id="flow-arrow"
                      viewBox="0 0 10 10"
                      refX="9"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
                    </marker>
                  </defs>
                  {flowEdges.map((edge) => {
                    const target = displayRun.stages.find(
                      (stage) => stage.stage === edge.target,
                    );
                    const recordedTarget = Boolean(
                      target?.started_at || target?.completed_at,
                    );
                    const active = replay
                      ? replayStage === edge.target
                      : connection === "connected" &&
                        target?.status === "processing";
                    const geometry = edgeGeometry(edge.source, edge.target);
                    return (
                      <g
                        key={edge.id}
                        className={`flow-edge ${replay && !replay.playing ? "is-paused" : ""} ${recordedTarget ? "flow-edge-recorded" : ""} ${active ? "flow-edge-active" : ""}`}
                      >
                        <path
                          className="flow-edge-path"
                          d={geometry.path}
                          markerEnd="url(#flow-arrow)"
                        />
                        {active && motion && (!replay || replay.playing) && (
                          <circle className="flow-packet" r="3.5">
                            <animateMotion
                              dur={`${1.4 / (replay ? speed : 1)}s`}
                              repeatCount="indefinite"
                              path={geometry.path}
                            />
                          </circle>
                        )}
                      </g>
                    );
                  })}
                </svg>
                {flowEdges.map((edge) => {
                  const geometry = edgeGeometry(edge.source, edge.target);
                  const target = flowSteps.find(
                    (step) => step.id === edge.target,
                  )!;
                  return (
                    <button
                      type="button"
                      key={edge.id}
                      data-testid={`flow-edge-${edge.source}-${edge.target}`}
                      className={`flow-edge-label ${geometry.vertical ? "is-vertical" : ""} ${selectedId === edge.target ? "is-selected" : ""}`}
                      style={{ left: geometry.x, top: geometry.y }}
                      aria-label={`Inspect ${edge.label} handoff to ${target.title}`}
                      onClick={() => selectStep(edge.target, "input")}
                    >
                      {edge.label}
                    </button>
                  );
                })}
                {flowSteps.map((step, index) => {
                  const stage = displayRun.stages.find(
                    (item) => item.stage === step.id,
                  );
                  const status = stage?.status ?? "waiting";
                  const replayIndex = recorded.findIndex(
                    (item) => item.stage === step.id,
                  );
                  const isPending =
                    replay && (replayIndex < 0 || replayIndex > replay.index);
                  return (
                    <button
                      type="button"
                      key={step.id}
                      data-testid={`flow-node-${step.id}`}
                      data-status={status}
                      data-tone={
                        index < 3
                          ? "blue"
                          : index < 6
                            ? "cyan"
                            : index < 9
                              ? "violet"
                              : "amber"
                      }
                      aria-label={`${index + 1}. ${step.title}, ${status}. ${step.component}`}
                      aria-pressed={selectedId === step.id}
                      className={`flow-node is-${status} ${selectedId === step.id ? "is-selected" : ""} ${replayStage === step.id ? "is-replay-focus" : ""} ${isPending ? "is-replay-pending" : ""}`}
                      style={{
                        left: positions[index][0],
                        top: positions[index][1],
                      }}
                      onClick={() => selectStep(step.id)}
                      onKeyDown={(event) => {
                        const offset =
                          event.key === "ArrowRight" ||
                          event.key === "ArrowDown"
                            ? 1
                            : event.key === "ArrowLeft" ||
                                event.key === "ArrowUp"
                              ? -1
                              : 0;
                        if (!offset) return;
                        event.preventDefault();
                        const next =
                          flowSteps[
                            (index + offset + flowSteps.length) %
                              flowSteps.length
                          ];
                        selectStep(next.id);
                        scene.current
                          ?.querySelector<HTMLButtonElement>(
                            `[data-testid="flow-node-${next.id}"]`,
                          )
                          ?.focus({ preventScroll: true });
                      }}
                    >
                      <span className="flow-node-icon">
                        <NodeIcon icon={step.icon} />
                      </span>
                      <span className="flow-node-title">{step.title}</span>
                      <span className="flow-node-component">
                        {step.component}
                      </span>
                      <span className="flow-node-footer">
                        <span className="flow-node-status">
                          {status === "completed" ? (
                            <Check size={12} />
                          ) : status === "processing" ? (
                            <Activity size={12} />
                          ) : status === "abstained" ? (
                            <Pause size={12} />
                          ) : (
                            <span className="flow-status-dot" />
                          )}
                          {status}
                        </span>
                        <span className="flow-node-time">
                          {duration(stage?.duration_ms)}
                        </span>
                      </span>
                    </button>
                  );
                })}
                <div
                  className="flow-map-note"
                  style={{
                    position: "absolute",
                    left: 46,
                    top: 561,
                    width: 250,
                  }}
                >
                  <Fingerprint size={19} />
                  <strong>Evidence at every step.</strong>
                  <span>One correlation ID connects the whole journey.</span>
                </div>
              </div>
            </div>
          </div>
          <div className="flow-legend">
            <span className="flow-legend-item">
              <i className="flow-legend-dot completed" />
              Recorded
            </span>
            <span className="flow-legend-item">
              <i className="flow-legend-dot processing" />
              Processing
            </span>
            <span className="flow-legend-item">
              <i className="flow-legend-dot waiting" />
              Waiting
            </span>
            <span className="flow-legend-item">
              <i className="flow-legend-dot blocked" />
              Boundary / error
            </span>
            <span className="flow-legend-hint">
              Drag to pan · select to inspect
            </span>
            <button
              className="flow-mobile-inspect"
              onClick={() =>
                document
                  .getElementById("flow-component-inspector")
                  ?.scrollIntoView({
                    behavior: motion ? "smooth" : "instant",
                    block: "start",
                  })
              }
            >
              Inspect {selectedInfo.title}
              <ArrowRight size={13} />
            </button>
          </div>
        </div>

        <aside
          id="flow-component-inspector"
          className="flow-inspector"
          data-testid="flow-inspector"
          aria-label="Selected component inspector"
        >
          <div className="flow-inspector-heading">
            <span className="flow-inspector-icon">
              <NodeIcon icon={selectedInfo.icon} />
            </span>
            <div>
              <p className="flow-panel-eyebrow">
                CHECKPOINT {String(selectedIndex + 1).padStart(2, "0")} / 11
              </p>
              <h3>{selectedInfo.title}</h3>
              <span>{selectedInfo.component}</span>
            </div>
          </div>
          <div className={`flow-stage-status is-${selectedStatus}`}>
            <span className="flow-status-dot" />
            {selectedStatus}
            {selectedStage?.attempt != null && (
              <small>Attempt {selectedStage.attempt}</small>
            )}
          </div>
          <p className="flow-inspector-description">
            {selectedInfo.description}
          </p>
          <dl className="flow-inspector-facts">
            <div>
              <dt>Duration</dt>
              <dd>{duration(selectedStage?.duration_ms)}</dd>
            </div>
            <div>
              <dt>Producer</dt>
              <dd>{selectedStage?.producer ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Started</dt>
              <dd>{date(selectedStage?.started_at)}</dd>
            </div>
            <div>
              <dt>Finished</dt>
              <dd>{date(selectedStage?.completed_at)}</dd>
            </div>
          </dl>
          {selectedStage?.error != null && (
            <div className="flow-stage-error" role="note">
              <Info size={15} />
              <span>
                {typeof selectedStage.error === "string"
                  ? selectedStage.error
                  : JSON.stringify(selectedStage.error)}
              </span>
            </div>
          )}
          <div
            className="flow-inspector-tabs"
            role="tablist"
            aria-label="Component evidence"
          >
            {(["input", "output"] as const).map((kind) => (
              <button
                type="button"
                key={kind}
                id={`flow-tab-${kind}`}
                role="tab"
                aria-selected={tab === kind}
                aria-controls="flow-payload-panel"
                tabIndex={tab === kind ? 0 : -1}
                className={tab === kind ? "active" : ""}
                onClick={() => setTab(kind)}
                onKeyDown={(event) => {
                  if (
                    ["ArrowLeft", "ArrowRight", "Home", "End"].includes(
                      event.key,
                    )
                  ) {
                    event.preventDefault();
                    const next =
                      event.key === "Home"
                        ? "input"
                        : event.key === "End"
                          ? "output"
                          : tab === "input"
                            ? "output"
                            : "input";
                    setTab(next);
                    document.getElementById(`flow-tab-${next}`)?.focus();
                  }
                }}
              >
                {kind === "input" ? (
                  <ArrowRight size={14} />
                ) : (
                  <Code2 size={14} />
                )}
                {kind === "input" ? "Input" : "Output"}
              </button>
            ))}
          </div>
          <div
            id="flow-payload-panel"
            role="tabpanel"
            aria-labelledby={`flow-tab-${tab}`}
            tabIndex={0}
          >
            <div className="flow-payload-bar">
              <span>Recorded {tab} evidence</span>
              <SmallButton label="Copy JSON" onClick={() => void copyPayload()}>
                {copyState === "Copied" ? (
                  <Check size={14} />
                ) : (
                  <Copy size={14} />
                )}
              </SmallButton>
            </div>
            {(!selectedStage ||
              (selectedStatus === "waiting" && !selectedStage.started_at)) && (
              <div className="flow-empty-payload">
                <Clock3 size={19} />
                <strong>Waiting for this checkpoint</strong>
                <p>
                  {selectedInfo.id === "decision"
                    ? "A human reviewer must record a decision."
                    : "Evidence will appear when the backend records this step."}
                </p>
              </div>
            )}
            <pre
              className="flow-code"
              tabIndex={0}
              aria-label={`Recorded ${tab} evidence JSON`}
            >
              <code>
                <JsonEvidence value={payload} />
              </code>
            </pre>
            <span className="flow-copy-status" role="status">
              {copyState}
            </span>
            <p className="flow-payload-note">
              <Info size={13} />
              Recorded references and evidence, not a capture of network
              messages.
            </p>
          </div>
          {selectedInfo.id === "decision" &&
            run.status === "AWAITING_REVIEW" &&
            !replay && (
              <button
                className="flow-button primary flow-review-callout"
                onClick={onReview}
              >
                Continue to human review
                <ArrowRight size={15} />
              </button>
            )}
        </aside>
      </div>

      <div className="flow-playback">
        <div className="flow-playback-header">
          <div>
            <p className="flow-panel-eyebrow">THE REQUEST, STEP BY STEP</p>
            <h3>
              {replay
                ? "Replay recorded evidence"
                : "Explore the transaction timeline"}
            </h3>
          </div>
          <div className="flow-playback-controls">
            {replay ? (
              <>
                <SmallButton
                  label="Previous replay step"
                  disabled={replay.index === 0}
                  onClick={() =>
                    setReplay({
                      ...replay,
                      inspectedId: undefined,
                      index: replay.index - 1,
                      playing: false,
                    })
                  }
                >
                  <ArrowLeft size={15} />
                </SmallButton>
                <button
                  className="flow-button primary"
                  onClick={() =>
                    setReplay({
                      ...replay,
                      inspectedId: undefined,
                      index:
                        replay.index === recorded.length - 1 ? 0 : replay.index,
                      playing: !replay.playing,
                    })
                  }
                >
                  {replay.playing ? <Pause size={14} /> : <Play size={14} />}
                  {replay.playing ? "Pause replay" : "Play replay"}
                </button>
                <SmallButton
                  label="Next replay step"
                  disabled={replay.index >= recorded.length - 1}
                  onClick={() =>
                    setReplay({
                      ...replay,
                      inspectedId: undefined,
                      index: replay.index + 1,
                      playing: false,
                    })
                  }
                >
                  <ArrowRight size={15} />
                </SmallButton>
                <label className="flow-speed-label">
                  <span className="sr-only">Replay speed</span>
                  <select
                    aria-label="Replay speed"
                    value={speed}
                    onChange={(event) => setSpeed(Number(event.target.value))}
                  >
                    <option value={0.5}>0.5×</option>
                    <option value={1}>1×</option>
                    <option value={2}>2×</option>
                  </select>
                </label>
                <button
                  className="flow-button subtle"
                  onClick={() => {
                    setReplay(null);
                    setFollow(true);
                  }}
                >
                  Return to live
                  <ArrowRight size={14} />
                </button>
              </>
            ) : (
              <button
                className="flow-button primary"
                disabled={recorded.length === 0}
                onClick={startReplay}
              >
                <Play size={14} />
                Replay recorded flow
              </button>
            )}
          </div>
        </div>
        {replay && (
          <div className="flow-mode-note" role="status">
            <RotateCcw size={14} />
            <span>
              {replay.playing
                ? "Playing"
                : replay.index === recorded.length - 1
                  ? "Replay complete"
                  : "Replay paused"}{" "}
              · {replay.index + 1} of {recorded.length} recorded checkpoints.
              Illustrative playback; timing is not to scale.
              {latestChanged
                ? " New backend evidence is available. Return to live to see it."
                : connection === "disconnected"
                  ? " The connection is interrupted; this replay uses saved evidence."
                  : terminal
                    ? " Return to live to inspect the latest loaded record."
                    : " Live collection continues in the background."}
            </span>
          </div>
        )}
        {replay && (
          <div className="flow-scrubber">
            <label className="sr-only" htmlFor="flow-replay-position">
              Replay position
            </label>
            <input
              id="flow-replay-position"
              type="range"
              min={0}
              max={Math.max(0, recorded.length - 1)}
              step={1}
              value={replay.index}
              aria-valuetext={`${replay.index + 1} of ${recorded.length}: ${flowSteps.find((step) => step.id === replayStage)?.title}`}
              onChange={(event) =>
                setReplay({
                  ...replay,
                  inspectedId: undefined,
                  index: Number(event.target.value),
                  playing: false,
                })
              }
            />
            <div className="flow-scrubber-labels">
              <span>First recorded step</span>
              <span>Latest recorded step</span>
            </div>
          </div>
        )}
        <div className="flow-timeline" aria-label="Transaction checkpoints">
          {flowSteps.map((step, index) => {
            const stage = displayRun.stages.find(
              (item) => item.stage === step.id,
            );
            return (
              <button
                key={step.id}
                className={`flow-timeline-step ${stage && ["completed", "abstained"].includes(stage.status) ? "is-recorded" : ""} ${selectedId === step.id ? "is-current" : ""}`}
                aria-pressed={selectedId === step.id}
                onClick={() => selectStep(step.id)}
              >
                <span className="flow-timeline-index">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="flow-timeline-name">{step.title}</span>
                <span className="flow-timeline-state">
                  {duration(stage?.duration_ms)}
                </span>
              </button>
            );
          })}
        </div>
        <p className="flow-footnote">
          <Info size={13} />
          {replay
            ? `Snapshot recorded ${date(replay.snapshot.updated_at)}. Replay does not execute or retry the transaction.`
            : "Live view reads persisted backend state. Connections show the workflow sequence; animation indicates activity, not individual network packets."}
        </p>
      </div>
    </section>
  );
}
