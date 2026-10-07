import { type Run, type Stage } from "./api";
import {
  Activity,
  Cloud,
  Database,
  FileCheck2,
  Fingerprint,
  GitBranch,
  Layers3,
  Network,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "./icons";

export type FlowStep = {
  id: string;
  title: string;
  component: string;
  description: string;
  icon: LucideIcon;
  message: string;
};

/** Canonical persisted stages from DemoStore.STAGES; these are logical handoffs. */
export const flowSteps: FlowStep[] = [
  {
    id: "submission",
    title: "Event submitted",
    component: "Java control plane",
    description:
      "Accepts the fictional source history and persists an event in the transactional outbox.",
    icon: Cloud,
    message: "Fictional source history",
  },
  {
    id: "publication",
    title: "Publish event",
    component: "Apache Kafka · producer",
    description:
      "Publishes the event to Kafka and records the broker receipt or confirmed delivery.",
    icon: Network,
    message: "Broker delivery evidence",
  },
  {
    id: "ingestion",
    title: "Consume event",
    component: "Java control plane · consumer",
    description:
      "Checks the delivered event against the outbox and records its durable inbox receipt.",
    icon: GitBranch,
    message: "Durable event receipt",
  },
  {
    id: "snapshot",
    title: "Build snapshot",
    component: "Python evidence runtime",
    description:
      "Projects source history into observation-time facts, model features, and a snapshot.",
    icon: Layers3,
    message: "Snapshot + feature projection",
  },
  {
    id: "score",
    title: "Score risk",
    component: "Python inference service",
    description:
      "Calls the released model and verifies its identity, probability, and advisory authority.",
    icon: Activity,
    message: "Released-model risk response",
  },
  {
    id: "rules",
    title: "Check eligibility",
    component: "Java eligibility engine",
    description:
      "Evaluates policy context against the deterministic action eligibility rules.",
    icon: ShieldCheck,
    message: "Eligibility results + context",
  },
  {
    id: "allocation",
    title: "Allocate resources",
    component: "Java portfolio allocator",
    description:
      "Values candidates through the Python runtime and selects within the demo resource budget.",
    icon: GitBranch,
    message: "Valuation + allocation result",
  },
  {
    id: "case",
    title: "Persist case",
    component: "PostgreSQL · Java control plane",
    description:
      "Persists the review case with references and digests for the recorded evidence.",
    icon: Database,
    message: "Persisted case + evidence digests",
  },
  {
    id: "agent",
    title: "Prepare review",
    component: "Python bounded agent",
    description:
      "Produces a cited draft for human review or records an abstention.",
    icon: Sparkles,
    message: "Bounded draft or abstention",
  },
  {
    id: "decision",
    title: "Human decision",
    component: "Reviewer · Java control plane",
    description:
      "Waits for an explicit human review, then commits the decision and updated case version.",
    icon: FileCheck2,
    message: "Committed review decision",
  },
  {
    id: "audit",
    title: "Verify audit",
    component: "PostgreSQL · SHA-256 verifier",
    description:
      "Verifies the persisted journal chain and records the verification result.",
    icon: Fingerprint,
    message: "Hash-chain verification result",
  },
];

export type FlowEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
};

/** Edges depict workflow order, not a packet capture or an exhaustive service map. */
export const flowEdges: FlowEdge[] = flowSteps
  .slice(0, -1)
  .map((step, index) => ({
    id: `${step.id}-${flowSteps[index + 1].id}`,
    source: step.id,
    target: flowSteps[index + 1].id,
    label: step.message,
  }));

const outputArtifacts: Record<string, string[]> = {
  snapshot: ["projection", "snapshot"],
  score: ["score"],
  rules: ["rules"],
  allocation: ["allocation"],
  agent: ["agent"],
  decision: ["decision"],
};

function referenceList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter(
        (reference): reference is string => typeof reference === "string",
      )
    : [];
}

function hasEvidence(stage: Stage): boolean {
  return Boolean(stage.evidence && Object.keys(stage.evidence).length);
}

/** The API persists references and outputs; it does not expose raw wire payloads. */
export function payloadForStep(
  run: Run,
  stepId: string,
  kind: "input" | "output",
): unknown {
  const stage = run.stages.find((candidate) => candidate.stage === stepId);
  if (!stage) {
    return {
      availability: "Not recorded",
      message: "This stage is not present in the run response.",
    };
  }

  if (kind === "input") {
    const refs = referenceList(stage.input_refs);
    const prefix = `run:${run.correlation_id}/`;
    const linkedRecords = refs.map((reference) => {
      const linkedId = reference.startsWith(prefix)
        ? reference.slice(prefix.length)
        : null;
      const linked = linkedId
        ? run.stages.find((candidate) => candidate.stage === linkedId)
        : undefined;
      return {
        reference,
        ...(linked
          ? {
              stage: linked.stage,
              status: linked.status,
              producer: linked.producer,
              recorded_evidence: hasEvidence(linked) ? linked.evidence : null,
              ...(!hasEvidence(linked)
                ? { availability: "No evidence recorded for this reference." }
                : {}),
            }
          : {
              availability:
                "Referenced evidence is not included in this run response.",
            }),
      };
    });
    return {
      description:
        "Recorded logical input references and their linked stage evidence. These are not captured network request bodies.",
      recorded_input_refs: refs,
      ...(linkedRecords.length
        ? { referenced_stage_records: linkedRecords }
        : {}),
      ...(stepId === "submission" && hasEvidence(stage)
        ? { accepted_source_history: stage.evidence }
        : {}),
      ...(!refs.length && !(stepId === "submission" && hasEvidence(stage))
        ? {
            availability:
              "No input references have been recorded for this stage.",
          }
        : {}),
    };
  }

  const artifactNames = outputArtifacts[stepId] ?? [];
  const artifacts = Object.fromEntries(
    artifactNames
      .filter((name) => run.artifacts[name] !== undefined)
      .map((name) => [name, run.artifacts[name]]),
  );
  return {
    description:
      "Persisted stage output and content-hash references from the run response.",
    stage: stage.stage,
    status: stage.status,
    producer: stage.producer,
    recorded_output_refs: referenceList(stage.output_refs),
    recorded_evidence: hasEvidence(stage) ? stage.evidence : null,
    ...(Object.keys(artifacts).length ? { recorded_artifacts: artifacts } : {}),
    ...(stage.error ? { recorded_error: stage.error } : {}),
    ...(!hasEvidence(stage)
      ? { availability: "No output evidence has been recorded for this stage." }
      : {}),
  };
}

/** Only persisted starts/completions participate in replay; waiting alone is not an event. */
export function recordedSteps(run: Run): Stage[] {
  return flowSteps.flatMap(({ id }) => {
    const stage = run.stages.find((candidate) => candidate.stage === id);
    return stage && (stage.started_at || stage.completed_at) ? [stage] : [];
  });
}
