import { useCallback, useEffect, useRef, useState } from "react";
import { type Run, type VisitorSession } from "./api";

export const RECENT_RUNS_KEY = "inforsight.recent-runs.v1";
const LIMIT = 20;
export type RecentRun = {
  correlation_id: string;
  scenario_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_opened_at: string;
  unavailable?: "removed" | "unavailable";
};

function readHistory(owner: string): RecentRun[] {
  const saved = JSON.parse(localStorage.getItem(RECENT_RUNS_KEY) ?? "null");
  if (
    saved?.version !== 1 ||
    saved?.owner !== owner ||
    !Array.isArray(saved.runs)
  )
    return [];
  const seen = new Set<string>();
  return saved.runs
    .filter((item: unknown): item is RecentRun => {
      if (!item || typeof item !== "object") return false;
      const row = item as RecentRun;
      if (
        ![row.correlation_id, row.scenario_id, row.status].every(
          (value) =>
            typeof value === "string" &&
            value.length > 0 &&
            value.length <= 200,
        )
      )
        return false;
      if (
        ![row.created_at, row.updated_at, row.last_opened_at].every(
          (value) =>
            typeof value === "string" && Number.isFinite(Date.parse(value)),
        )
      )
        return false;
      if (seen.has(row.correlation_id)) return false;
      seen.add(row.correlation_id);
      return true;
    })
    .sort(
      (a: RecentRun, b: RecentRun) =>
        Date.parse(b.last_opened_at) - Date.parse(a.last_opened_at),
    )
    .slice(0, LIMIT);
}

/** Store navigation metadata only, never payloads, credentials, or case evidence. */
export function useRecentRuns(run: Run | null, session: VisitorSession | null) {
  const owner = session?.session_tag;
  const [entries, setEntries] = useState<RecentRun[]>([]);
  const [persistent, setPersistent] = useState(true);
  const current = useRef<RecentRun[]>([]);
  const storageWritable = useRef(true);
  const opened = useRef<{ id: string; at: string } | null>(null);

  useEffect(() => {
    opened.current = null;
    storageWritable.current = true;
    const refresh = () => {
      let rows: RecentRun[] = [];
      try {
        rows = owner ? readHistory(owner) : [];
      } catch {
        /* Damaged or unavailable storage starts with an empty list. */
      }
      current.current = rows;
      setEntries(rows);
    };
    refresh();
    const onStorage = (event: StorageEvent) => {
      if (event.key === RECENT_RUNS_KEY || event.key === null) refresh();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [owner]);

  const update = useCallback(
    (change: (rows: RecentRun[]) => RecentRun[]) => {
      if (!owner) return;
      let rows = current.current;
      try {
        if (storageWritable.current) rows = readHistory(owner);
      } catch {
        /* Keep this tab's history if storage is unavailable. */
      }
      const next = change(rows).slice(0, LIMIT);
      current.current = next;
      setEntries(next);
      try {
        localStorage.setItem(
          RECENT_RUNS_KEY,
          JSON.stringify({ version: 1, owner, runs: next }),
        );
        setPersistent(true);
        storageWritable.current = true;
      } catch {
        setPersistent(false);
        storageWritable.current = false;
      }
    },
    [owner],
  );

  useEffect(() => {
    if (!run || !owner) {
      opened.current = null;
      return;
    }
    const newVisit = opened.current?.id !== run.correlation_id;
    if (newVisit)
      opened.current = { id: run.correlation_id, at: new Date().toISOString() };
    const openedAt = opened.current!.at;
    update((rows) => {
      const previous = rows.find(
        (row) => row.correlation_id === run.correlation_id,
      );
      // A background poll must not restore history cleared in another tab.
      if (!previous && !newVisit) return rows;
      const latest =
        previous && Date.parse(previous.updated_at) > Date.parse(run.updated_at)
          ? previous
          : run;
      const entry: RecentRun = {
        correlation_id: run.correlation_id,
        scenario_id: run.scenario_id,
        status: latest.status,
        created_at: run.created_at,
        updated_at: latest.updated_at,
        last_opened_at:
          previous && Date.parse(previous.last_opened_at) > Date.parse(openedAt)
            ? previous.last_opened_at
            : openedAt,
      };
      return [
        entry,
        ...rows.filter((row) => row.correlation_id !== run.correlation_id),
      ].sort(
        (a, b) => Date.parse(b.last_opened_at) - Date.parse(a.last_opened_at),
      );
    });
  }, [run, owner, update]);

  const markUnavailable = useCallback(
    (id: string, status: number) => {
      update((rows) =>
        rows.map((row) =>
          row.correlation_id === id
            ? {
                ...row,
                unavailable: status === 410 ? "removed" : "unavailable",
              }
            : row,
        ),
      );
    },
    [update],
  );

  return {
    entries,
    persistent,
    markUnavailable,
    remove: (id: string) =>
      update((rows) => rows.filter((row) => row.correlation_id !== id)),
    clear: () => update(() => []),
  };
}
