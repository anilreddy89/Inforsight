import { useEffect, useRef, useState } from "react";
import { ArrowRight, Clock3, FileText, Info, RotateCcw, X } from "./icons";
import { date, words } from "./api";
import { type RecentRun } from "./recent-runs";
import "./recent-runs.css";

export default function RecentRuns({
  open,
  entries,
  persistent,
  titleFor,
  onDismiss,
  onOpen,
  onRemove,
  onClear,
}: {
  open: boolean;
  entries: RecentRun[];
  persistent: boolean;
  titleFor: (scenario: string) => string;
  onDismiss: () => void;
  onOpen: (id: string) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (open && !dialog.current?.open) {
      setQuery("");
      dialog.current?.showModal();
    } else if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);
  const search = query.trim().toLowerCase();
  const matches = entries.filter((entry) =>
    `${titleFor(entry.scenario_id)} ${entry.correlation_id} ${words(entry.status)}`
      .toLowerCase()
      .includes(search),
  );
  return (
    <dialog
      ref={dialog}
      className="recent-runs-dialog"
      aria-labelledby="recent-runs-title"
      aria-describedby="recent-runs-description"
      onCancel={onDismiss}
      onClose={onDismiss}
    >
      <div className="recent-runs-heading">
        <span className="recent-runs-icon">
          <RotateCcw size={22} />
        </span>
        <div>
          <p className="eyebrow">PICK UP WHERE YOU LEFT OFF</p>
          <h2 id="recent-runs-title">Recent runs</h2>
        </div>
        <button
          className="recent-runs-close"
          type="button"
          aria-label="Close recent runs"
          onClick={onDismiss}
          autoFocus
        >
          <X size={20} />
        </button>
      </div>
      <p id="recent-runs-description">
        Your last 20 cases opened in this browser, most recent first. Select a
        case to continue its journey.
      </p>
      {entries.length > 0 && (
        <div className="recent-runs-search">
          <label htmlFor="recent-runs-search">Find a run</label>
          <input
            id="recent-runs-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search scenario, status, or correlation ID"
            autoComplete="off"
          />
          <span role="status">
            {matches.length} {matches.length === 1 ? "run" : "runs"}
            {search ? " found" : " saved"}
          </span>
        </div>
      )}
      <div className="recent-runs-list">
        {matches.length ? (
          <ul>
            {matches.map((entry) => (
              <li key={entry.correlation_id}>
                <button
                  className="recent-run-open"
                  type="button"
                  onClick={() => onOpen(entry.correlation_id)}
                  aria-label={`Open ${titleFor(entry.scenario_id)}, ${entry.correlation_id}`}
                >
                  <span className="recent-run-icon">
                    <FileText size={19} />
                  </span>
                  <span className="recent-run-summary">
                    <strong>{titleFor(entry.scenario_id)}</strong>
                    <code>{entry.correlation_id}</code>
                    <span className="recent-run-date">
                      <Clock3 size={12} />
                      Last opened {date(entry.last_opened_at)}
                    </span>
                    <span
                      className={`recent-run-status badge badge-${entry.unavailable ? "blocked" : entry.status.toLowerCase()}`}
                    >
                      {entry.unavailable === "removed"
                        ? "Removed by retention"
                        : entry.unavailable
                          ? "Unavailable when last opened"
                          : words(entry.status)}
                    </span>
                  </span>
                  <ArrowRight size={17} className="recent-run-arrow" />
                </button>
                <button
                  className="recent-run-remove"
                  type="button"
                  onClick={() => onRemove(entry.correlation_id)}
                  aria-label={`Remove ${entry.correlation_id} from recent runs`}
                  title="Remove from this browser’s list"
                >
                  <X size={15} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="recent-runs-empty">
            <Clock3 size={32} />
            <h3>
              {search
                ? "No matching runs"
                : "Your next case starts your history"}
            </h3>
            <p>
              {search
                ? "Try a scenario name, a status, or part of a correlation ID."
                : "Start a case or reopen one with its correlation ID. It will be saved here automatically for your next visit."}
            </p>
            {search && (
              <button
                type="button"
                className="text-link"
                onClick={() => setQuery("")}
              >
                Clear search
              </button>
            )}
          </div>
        )}
      </div>
      <div className="recent-runs-footer">
        <p>
          <Info size={15} />
          <span>
            {persistent
              ? "Saved on this browser only. Status reflects the last visit; opening a run checks its current availability. Cases may expire."
              : "Browser storage is unavailable. This history is available in this tab until you reload."}
          </span>
        </p>
        {entries.length > 0 && (
          <button type="button" className="text-link" onClick={onClear}>
            Clear recent history
          </button>
        )}
        <span className="recent-runs-retention">
          Removing history does not delete any backend cases.
        </span>
      </div>
    </dialog>
  );
}
