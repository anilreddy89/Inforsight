import { ArrowRight } from "./icons";
import { lensCatalog, type LensId } from "./architecture-lenses";
import "./architecture-teaser.css";

/** Small illustrative map; the explorer itself shows the full, evidence-bound design. */
const previewNodes = [
  { id: "browser", label: "Browser", x: 14, y: 106, tone: "#4b7cf0" },
  { id: "gateway", label: "nginx", x: 120, y: 106, tone: "#2fb39a" },
  { id: "java", label: "Java", x: 226, y: 106, tone: "#8d74e8" },
  { id: "kafka", label: "Kafka", x: 226, y: 22, tone: "#2fbad6" },
  { id: "postgres", label: "PostgreSQL", x: 226, y: 190, tone: "#5b8fd6" },
  { id: "model", label: "Model", x: 336, y: 64, tone: "#d5679b" },
  { id: "agent", label: "Agent", x: 336, y: 148, tone: "#4cb57a" },
];
const previewEdges = [
  "M 98 125 H 120",
  "M 204 125 H 226",
  "M 268 106 V 64",
  "M 268 144 V 190",
  "M 310 112 C 322 104, 324 92, 336 86",
  "M 310 138 C 322 146, 324 158, 336 166",
];
const previewPath = "M 56 125 H 268 V 41";

function TeaserPreview() {
  return (
    <div className="architecture-teaser-preview" aria-hidden="true">
      <span className="architecture-teaser-caption">Illustrative preview</span>
      <svg viewBox="0 0 430 236" role="presentation">
        {previewEdges.map((path) => (
          <path key={path} className="teaser-edge" d={path} />
        ))}
        <path className="teaser-route" d={previewPath} />
        <circle className="teaser-packet" r="4">
          <animateMotion dur="3.2s" repeatCount="indefinite" path={previewPath} />
        </circle>
        {previewNodes.map((node) => (
          <g key={node.id} className={`teaser-node ${node.id === "java" ? "is-active" : ""}`}>
            <rect x={node.x} y={node.y} width={84} height={38} rx={8} />
            <rect className="teaser-accent" x={node.x} y={node.y + 9} width={3} height={20} rx={1.5} fill={node.tone} />
            <text x={node.x + 46} y={node.y + 24} textAnchor="middle">
              {node.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function ArchitectureTeaser({ onOpen }: { onOpen: (lens?: LensId) => void }) {
  return (
    <section
      className="architecture-teaser"
      aria-labelledby="architecture-teaser-title"
      data-testid="architecture-teaser"
    >
      <div className="content-width">
        <div className="architecture-teaser-top">
          <div className="architecture-teaser-copy">
            <p className="eyebrow">INSIDE THE SYSTEM</p>
            <h2 id="architecture-teaser-title">See every component behind a decision.</h2>
            <p>
              Seven interactive diagrams drawn from the code: containers and trust boundaries,
              every request in order, how the model was built, and how each step is hashed.
              Open a case first and they follow it live.
            </p>
            <button type="button" className="button primary" onClick={() => onOpen()}>
              Open the architecture explorer
              <ArrowRight size={16} aria-hidden="true" />
            </button>
          </div>
          <TeaserPreview />
        </div>
        <ul className="architecture-teaser-lenses" aria-label="Architecture views">
          {lensCatalog.map((lens) => (
            <li key={lens.id}>
              <button
                type="button"
                data-testid={`teaser-lens-${lens.id}`}
                onClick={() => onOpen(lens.id)}
              >
                <span className="architecture-teaser-icon">
                  <lens.icon size={18} aria-hidden="true" />
                </span>
                <span className="architecture-teaser-text">
                  <strong>{lens.tab}</strong>
                  <span>{lens.blurb}</span>
                </span>
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
