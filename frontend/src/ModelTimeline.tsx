import { useEffect, useState, type CSSProperties } from "react";
import { ArrowLeft, ArrowRight, ArrowUpRight, Info, ShieldCheck } from "./icons";
import { GenerationTrack } from "./ModelBand";
import { milestones, modelStats, principles, recordUrl, verdictIcon } from "./model-history";
import "./model-timeline.css";

/** How the released model was reached: six generations, judged by pre-declared gates. */
export default function ModelTimeline({
  backLabel,
  onBack,
  focus,
  onOpenLineage,
}: {
  backLabel: string;
  onBack: () => void;
  focus?: string;
  onOpenLineage: () => void;
}) {
  const [highlight, setHighlight] = useState<string | null>(null);

  const jump = (id: string) => {
    const element = document.getElementById(`model-step-${id}`);
    if (!element) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    element.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" });
    element.focus({ preventScroll: true });
    setHighlight(id);
  };
  useEffect(() => {
    if (focus) jump(focus);
  }, [focus]);
  useEffect(() => {
    if (!highlight) return;
    const timer = window.setTimeout(() => setHighlight(null), 2400);
    return () => window.clearTimeout(timer);
  }, [highlight]);

  return (
    <div className="model-page content-width" data-testid="model-timeline">
      <button type="button" className="text-link back" onClick={onBack}>
        <ArrowLeft size={14} aria-hidden="true" />
        {backLabel}
      </button>
      <header className="model-intro">
        <p className="eyebrow accent">
          <span className="tiny-line" />
          HOW THE MODEL WAS BUILT
        </p>
        <h1>Six generations to one model we could defend.</h1>
        <p>
          We did not start from a formula. Each generation was a hypothesis, judged by gates
          written down in advance. Five were stopped by the evidence; every stop, and the one
          rule change made after results, is on the record.
        </p>
        <p className="model-span">Aug 17 – Sep 5, 2026 · from the first decision record to the released model</p>
      </header>

      <GenerationTrack label="Generations at a glance" onSelect={jump} />

      <ul className="model-stats" aria-label="Development in numbers">
        {modelStats.map((stat) => (
          <li key={stat.label}>
            <strong>{stat.value}</strong>
            <span>{stat.label}</span>
          </li>
        ))}
      </ul>

      <div className="model-layout">
        <ol className="model-steps" aria-label="Development timeline">
          {milestones.map((milestone, index) => {
            const Icon = verdictIcon[milestone.verdict];
            return (
              <li
                key={milestone.id}
                id={`model-step-${milestone.id}`}
                data-testid={`model-step-${milestone.id}`}
                tabIndex={-1}
                className={`model-step verdict-${milestone.verdict} ${highlight === milestone.id ? "is-highlighted" : ""}`}
                style={{ "--step-index": index } as CSSProperties}
                aria-labelledby={`model-step-title-${milestone.id}`}
              >
                <span className="model-step-marker" aria-hidden="true">
                  <Icon size={15} />
                </span>
                <article className="model-step-card">
                  <div className="model-step-top">
                    <span className="model-step-label">{milestone.label}</span>
                    <span className="model-step-date">{milestone.date}</span>
                    <span className="model-verdict">{milestone.verdictLabel}</span>
                  </div>
                  <h3 id={`model-step-title-${milestone.id}`}>{milestone.title}</h3>
                  <dl className="model-step-facts">
                    <div>
                      <dt>Tried</dt>
                      <dd>{milestone.tried}</dd>
                    </div>
                    <div>
                      <dt>Found</dt>
                      <dd>{milestone.found}</dd>
                    </div>
                    <div>
                      <dt>Learned</dt>
                      <dd>{milestone.learned}</dd>
                    </div>
                  </dl>
                  <div className="model-step-foot">
                    <span className="model-metric">{milestone.metric}</span>
                    <span className="model-step-records">
                      {milestone.records.map((record) => (
                        <a key={record.path} href={recordUrl(record.path)} target="_blank" rel="noopener noreferrer">
                          {record.label}
                          <ArrowUpRight size={13} aria-hidden="true" />
                          <span className="sr-only"> (opens on GitHub in a new tab)</span>
                        </a>
                      ))}
                    </span>
                  </div>
                </article>
              </li>
            );
          })}
        </ol>

        <div className="model-aside">
          <section className="model-panel" aria-labelledby="model-principles-title">
            <h2 id="model-principles-title">How every step was judged</h2>
            <ul className="model-principles">
              {principles.map((principle) => (
                <li key={principle.title}>
                  <ShieldCheck size={16} aria-hidden="true" />
                  <div>
                    <strong>{principle.title}</strong>
                    <span>{principle.text}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
          <section className="model-panel model-current" aria-labelledby="model-current-title">
            <p className="eyebrow">IN THIS DEMO</p>
            <h2 id="model-current-title">The released model</h2>
            <dl>
              <div>
                <dt>Model</dt>
                <dd>L2 logistic regression with Platt calibration</dd>
              </div>
              <div>
                <dt>Bundle</dt>
                <dd>
                  <code>inforsight-v6-logistic-platt-20260817</code> · v1.0.0
                </dd>
              </div>
              <div>
                <dt>SHA-256</dt>
                <dd>
                  <code>7ac292136d52…f37f12c656</code>
                </dd>
              </div>
              <div>
                <dt>Out of sample</dt>
                <dd>AUC 0.6998 · calibration error 0.0115</dd>
              </div>
            </dl>
            <button type="button" className="button secondary full" onClick={onOpenLineage}>
              See how it scores a case
              <ArrowRight size={15} aria-hidden="true" />
            </button>
          </section>
        </div>
      </div>

      <p className="model-footnote">
        <Info size={14} aria-hidden="true" />
        These results show that the models recover a synthetic data-generating process under a
        pre-declared protocol. They do not establish real-world predictive performance, actuarial
        validity, causality, fairness or production readiness.
      </p>
    </div>
  );
}
