import "../styles/budget.css";

function Meter({ name, snap }) {
  const remaining = snap?.remaining_requests;
  const limit = snap?.limit_requests;
  const known = Number.isFinite(remaining) && Number.isFinite(limit) && limit > 0;
  const pct = known ? Math.max(0, Math.min(100, (remaining / limit) * 100)) : null;
  const tokens = snap?.remaining_tokens;

  return (
    <div className="budget-meter">
      <div className="budget-meter-head">
        <span className="budget-name">{name}</span>
        <span className="budget-nums">
          {known ? `${remaining}/${limit}` : "—"}
          {Number.isFinite(tokens) ? ` · ${tokens}` : ""}
        </span>
      </div>
      <div className="budget-track" aria-hidden="true">
        <div className="budget-fill" style={{ width: `${pct == null ? 0 : pct}%` }} />
      </div>
    </div>
  );
}

export default function BudgetBar({ budget, sendMode, onToggleSend, toggling }) {
  return (
    <div className="budget-bar">
      <Meter name="Groq" snap={budget?.groq} />
      <Meter name="OpenRouter" snap={budget?.openrouter} />
      <label className={`send-toggle ${sendMode === "live" ? "is-live" : ""}`}>
        <input
          type="checkbox"
          checked={sendMode === "live"}
          disabled={toggling}
          onChange={(e) => onToggleSend(e.target.checked ? "live" : "dry_run")}
        />
        <span className="send-switch" aria-hidden="true" />
        <span>{sendMode === "live" ? "Live" : "Dry-run"}</span>
      </label>
    </div>
  );
}
