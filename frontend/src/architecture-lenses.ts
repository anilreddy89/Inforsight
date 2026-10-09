import {
  Boxes,
  Link2,
  ListOrdered,
  Shield,
  Table2,
  Waypoints,
  Workflow,
  type LucideIcon,
} from "./icons";

/**
 * The explorer's views, kept separate from the large architecture model so the
 * landing page and header can link into a view without loading the model.
 */
export type LensId =
  | "system"
  | "sequence"
  | "lineage"
  | "lifecycle"
  | "security"
  | "audit"
  | "schema";

export const lensCatalog: { id: LensId; tab: string; icon: LucideIcon; blurb: string }[] = [
  { id: "system", tab: "System map", icon: Boxes, blurb: "Containers, networks, ports and trust boundaries" },
  { id: "sequence", tab: "Request sequence", icon: ListOrdered, blurb: "All 42 calls of one run, in order" },
  { id: "lineage", tab: "Data & model lineage", icon: Waypoints, blurb: "From simulated history to a pinned model and verified evidence" },
  { id: "lifecycle", tab: "Run lifecycle", icon: Workflow, blurb: "Every state a run, stage and case can reach" },
  { id: "security", tab: "Security layers", icon: Shield, blurb: "Each control between the internet and the journal" },
  { id: "audit", tab: "Audit chain", icon: Link2, blurb: "How every recorded transition is hashed and verified" },
  { id: "schema", tab: "Database schema", icon: Table2, blurb: "The eleven tables behind every run" },
];

export function lensMeta(id: LensId) {
  const { tab, icon } = lensCatalog.find((lens) => lens.id === id)!;
  return { id, tab, icon };
}
