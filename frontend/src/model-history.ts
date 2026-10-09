import {
  CheckCircle2,
  CircleX,
  Layers3,
  Package,
  Pause,
  RotateCcw,
  type LucideIcon,
} from "./icons";

/**
 * How the released risk model was reached. Dates come from the repository history;
 * every figure comes from the linked records, frozen at the release tag.
 */
export type Verdict = "foundation" | "paused" | "stopped" | "redesign" | "proceed" | "released";

export type Milestone = {
  id: string;
  marker: string;
  label: string;
  date: string;
  title: string;
  tried: string;
  found: string;
  learned: string;
  verdict: Verdict;
  verdictLabel: string;
  /** Short text under the milestone's chip in the generation track. */
  short: string;
  metric: string;
  records: { label: string; path: string }[];
};

export const RELEASE_TAG = "v0.2.0-risk-model";
export const recordUrl = (path: string) =>
  `https://github.com/anilreddy89/Inforsight/blob/${RELEASE_TAG}/${path}`;

export const milestones: Milestone[] = [
  {
    id: "groundwork",
    marker: "0",
    label: "Groundwork",
    date: "Aug 17–18",
    title: "Rules and data before any model",
    tried:
      "Committed to clean-room synthetic data and to keeping risk scores apart from any action, then built versioned event contracts and point-in-time reconstruction.",
    found: "A reproducible fictional portfolio whose history can be replayed as of any date.",
    learned: "A feature may use only what was known on the observation date.",
    verdict: "foundation",
    verdictLabel: "Foundation set",
    short: "Foundation",
    metric: "3 decision records",
    records: [{ label: "First decision record", path: "docs/adr/0001-clean-room-and-synthetic-data.md" }],
  },
  {
    id: "v1",
    marker: "v1",
    label: "Generation 1",
    date: "Aug 19–20",
    title: "First baseline models",
    tried: "Logistic regression and XGBoost on the first simulator, with leakage guards and chronological splits.",
    found:
      "Validation AUC of 0.53–0.56 on just 27 records, close to chance. Three claim-blocking limitations were recorded, including billing frequency confounded with time.",
    learned: "The pipeline worked, but the data had no designed risk signal to learn. Results were limited to pipeline engineering.",
    verdict: "paused",
    verdictLabel: "Paused by review",
    short: "Paused",
    metric: "AUC 0.53–0.56",
    records: [{ label: "Limitation register", path: "docs/limitations.md" }],
  },
  {
    id: "v2",
    marker: "v2",
    label: "Generation 2",
    date: "Aug 29",
    title: "Multi-cohort hazards",
    tried: "Multiple issuance cohorts, a stochastic lapse mechanism and latent frailty, judged by a gate declared in advance.",
    found:
      "Baselines reached AUC 0.54–0.55. Before acceptance, a readiness audit found events recorded after the cutoff leaking into features, one of eight failed readiness rules.",
    learned: "An event counts only if it took effect and was recorded before the cutoff.",
    verdict: "stopped",
    verdictLabel: "Stopped before acceptance",
    short: "Stopped",
    metric: "8 readiness rules failed",
    records: [{ label: "Decision record", path: "docs/experiments/phase-02r-07-v2-statistical-acceptance-decision.md" }],
  },
  {
    id: "v3",
    marker: "v3",
    label: "Generation 3",
    date: "Sep 1",
    title: "Dual-time data and a 20-seed gate",
    tried: "Event-first dual-time data with matched null controls. Acceptance needed 16 of 20 seeds to reach AUC 0.65.",
    found: "Median AUC 0.519. No seed reached 0.65.",
    learned:
      "Follow-up diagnostics showed the simulated signal was too weak to learn. The thresholds stayed frozen; the design changed instead.",
    verdict: "redesign",
    verdictLabel: "Redesign",
    short: "Redesign",
    metric: "AUC 0.519 · 0 of 20 seeds",
    records: [{ label: "Decision record", path: "docs/experiments/phase-02r-11-v3-statistical-acceptance-decision.md" }],
  },
  {
    id: "v4",
    marker: "v4",
    label: "Generation 4",
    date: "Sep 2",
    title: "Amplified signal",
    tried: "Doubled every risk coefficient, cut unobserved frailty from 0.35 to 0.20 and gave payment counts realistic variation.",
    found:
      "The best AUC observable data allowed rose only to 0.567, and peak monthly hazard reached 0.218 against a 0.20 ceiling.",
    learned:
      "A stronger signal barely helped and already pushed lapse rates past the realistic limit. The cause had to be isolated before another design.",
    verdict: "redesign",
    verdictLabel: "Redesign",
    short: "Redesign",
    metric: "Oracle AUC 0.567 · hazard 0.218",
    records: [{ label: "Decision record", path: "docs/adr/0008-authorize-post-v4-redesign-diagnostics.md" }],
  },
  {
    id: "v5",
    marker: "v5",
    label: "Generation 5",
    date: "Sep 3",
    title: "Searching for any workable setting",
    tried:
      "Stopped once because the diagnostic thresholds were undefined, froze them as exact truth tables, then ran 17 diagnostics, including a 320-setting search.",
    found:
      "No setting reached AUC 0.70; the best was 0.593. Larger coefficients pushed peak monthly hazard as high as 0.88 without improving AUC.",
    learned:
      "No setting of the additive proportional-hazards design recovered the signal at a realistic lapse rate, so the hazard link itself had to change.",
    verdict: "stopped",
    verdictLabel: "Stopped: infeasible",
    short: "Infeasible",
    metric: "0 of 320 feasible",
    records: [{ label: "Decision record", path: "docs/adr/0011-record-v5-design-infeasibility-and-stop.md" }],
  },
  {
    id: "v6",
    marker: "v6",
    label: "Generation 6",
    date: "Sep 4",
    title: "Bounded sigmoid hazard",
    tried:
      "A bounded logistic hazard link that caps monthly hazard at 0.15 by construction. Logistic regression beat XGBoost on selection data (AUC 0.706 vs 0.680).",
    found:
      "On 20 reserved seeds: median AUC 0.7031, all 20 at or above 0.65, and every primary gate passed. Four secondary checks failed, so Protocol 3.0.0 returned redesign.",
    learned:
      "The bounded link recovered the signal while monthly hazard stayed at or below 0.15. After those results, ADR 0013 revised the four secondary thresholds with a stated rationale and left every primary gate unchanged. The re-run on the same seeds under Protocol 3.1.0 returned proceed.",
    verdict: "proceed",
    verdictLabel: "Proceed under Protocol 3.1.0",
    short: "Proceed",
    metric: "AUC 0.7031 · 20/20 seeds",
    records: [
      { label: "Amendment", path: "docs/adr/0013-amend-v6-statistical-acceptance-protocol.md" },
      { label: "Decision record", path: "docs/experiments/phase-02r-16-v6-statistical-acceptance-decision.md" },
    ],
  },
  {
    id: "release",
    marker: "★",
    label: "Release",
    date: "Sep 5",
    title: "Calibrated, explained and released",
    tried:
      "Platt calibration, per-feature explanations and a pinned model bundle, then one final evaluation against six pre-registered gates.",
    found:
      "AUC 0.6998 and calibration error 0.0115 on 8,782 out-of-sample observations, with all six gates passed. Reviewing the top 5% finds lapses at 2.31× the base rate.",
    learned: "The released bundle is the exact model that scores cases in this demo, pinned by its SHA-256.",
    verdict: "released",
    verdictLabel: "Released",
    short: "v0.2.0",
    metric: "v0.2.0 · ECE 0.0115",
    records: [{ label: "Model card", path: "MODEL_CARD.md" }],
  },
];

export const generations = milestones.filter((milestone) => milestone.marker.startsWith("v"));

export const modelStats: { value: string; label: string }[] = [
  { value: "6", label: "generations of the data design" },
  { value: "5", label: "stopped or sent back by evidence" },
  { value: "13", label: "decision records before release" },
  { value: "20", label: "reserved seeds in the final gate" },
  { value: "320", label: "settings searched for a feasible design" },
  { value: "6/6", label: "pre-registered release gates passed" },
];

export const principles: { title: string; text: string }[] = [
  {
    title: "Thresholds set before results",
    text: "Every acceptance rule was frozen before its run. The one change made after seeing acceptance results, to four secondary checks in generation 6, is on the record with its rationale.",
  },
  { title: "Mechanical verdicts", text: "From generation 2 on, a versioned protocol computed each verdict: proceed, redesign or stop." },
  { title: "No peeking at the future", text: "Features use only what was known at the cutoff. A leak caught in generation 2 stopped that run." },
  { title: "Many seeds, not one lucky run", text: "From generation 3 on, every verdict was judged across 20 independent seeds." },
  { title: "Every pivot on the record", text: "Each stop, redesign, amendment and release has a dated record of its evidence." },
  {
    title: "Final holdout kept sealed",
    text: "The final release holdout was never created. Release figures come from a separate out-of-sample partition.",
  },
];

export const verdictIcon: Record<Verdict, LucideIcon> = {
  foundation: Layers3,
  paused: Pause,
  stopped: CircleX,
  redesign: RotateCcw,
  proceed: CheckCircle2,
  released: Package,
};
