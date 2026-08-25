import { DRAFT_STAGES, pillTone, stageLabel } from "../stages.js";
import "../styles/leadcard.css";

export default function LeadCard({ lead, selected, onSelect }) {
  const tone = pillTone(lead.stage);
  const handle = lead.github_handle || "unknown";
  const project = lead.project || (lead.repo ? String(lead.repo).split("/").pop() : "—");
  const score = lead.fit_score == null ? "—" : lead.fit_score;
  const hasDraft = DRAFT_STAGES.has(lead.stage);

  const inner = (
    <>
      <div className="lead-card-top">
        <span className="lead-handle">@{handle}</span>
        <span className={`pill ${tone}`}>{stageLabel(lead.stage)}</span>
      </div>
      <div className="lead-project">{project}</div>
      <div className="lead-score">
        <span>fit</span>
        <span>{score}</span>
      </div>
      {hasDraft ? <div className="lead-draft-hint">View draft</div> : null}
    </>
  );

  if (!onSelect) {
    return <div className={`lead-card ${selected ? "is-selected" : ""}`}>{inner}</div>;
  }

  return (
    <button
      type="button"
      className={`lead-card is-button ${selected ? "is-selected" : ""}`}
      onClick={() => onSelect(lead.id)}
    >
      {inner}
    </button>
  );
}
