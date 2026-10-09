import { ArrowRight, History } from "./icons";
import { generations, milestones, verdictIcon } from "./model-history";
import "./model-band.css";

const release = milestones.find((milestone) => milestone.id === "release")!;

/** v1–v6 and the release as chips; each opens its milestone in the timeline. */
export function GenerationTrack({ onSelect, label }: { onSelect: (id: string) => void; label: string }) {
  return (
    <ol className="model-track" aria-label={label}>
      {[...generations, release].map((milestone) => {
        const Icon = verdictIcon[milestone.verdict];
        return (
          <li key={milestone.id}>
            <button
              type="button"
              className={`model-chip verdict-${milestone.verdict}`}
              data-testid={`model-chip-${milestone.id}`}
              title={`${milestone.label}: ${milestone.verdictLabel}`}
              onClick={() => onSelect(milestone.id)}
            >
              <span className="model-chip-dot">
                <Icon size={17} aria-hidden="true" />
              </span>
              <strong>{milestone.marker === "★" ? "Release" : milestone.marker}</strong>
              <small>{milestone.short}</small>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

/** Landing-page summary that opens the full model timeline. */
export default function ModelBand({ onOpen }: { onOpen: (step?: string) => void }) {
  return (
    <section className="model-band" aria-labelledby="model-band-title" data-testid="model-band">
      <div className="content-width model-band-inner">
        <div className="model-band-copy">
          <p className="eyebrow">HOW THE MODEL WAS BUILT</p>
          <h2 id="model-band-title">Six generations. Five stopped by evidence. One released.</h2>
          <p>
            The risk model was not picked from a formula. See each design we tried, what the
            tests showed, and why we changed course before releasing one we could defend.
          </p>
          <button type="button" className="button secondary" onClick={() => onOpen()}>
            <History size={16} aria-hidden="true" />
            See the model timeline
            <ArrowRight size={15} aria-hidden="true" />
          </button>
        </div>
        <div>
          <GenerationTrack label="Model generations at a glance" onSelect={onOpen} />
          <p className="model-band-note">
            Aug 17 – Sep 5, 2026 · 13 decision records · 20-seed final gate
          </p>
        </div>
      </div>
    </section>
  );
}
