import { useState } from "react";
import { pillTone, stageLabel } from "../stages.js";
import { simulateReply } from "../api.js";
import "../styles/receipt.css";

function providerTone(provider) {
  if (provider === "groq") return "groq";
  if (provider === "openrouter") return "openrouter";
  if (provider === "github") return "github";
  if (provider === "dry_run" || provider === "smtp") return "send";
  return "plain";
}

function stepTone(entry) {
  const out = (entry.output || "").toUpperCase();
  if (entry.step === "critic" && out.includes("FAIL")) return "fail";
  if (entry.step === "critic" && out.includes("PASS")) return "pass";
  if (entry.step === "sender") return "pass";
  if (entry.step === "orchestrator") return "fail";
  return "pending";
}

function splitEmail(body) {
  const text = (body || "").trim();
  const match = text.match(/^Subject:\s*(.+?)\n+([\s\S]*)$/i);
  if (match) return { subject: match[1].trim(), body: match[2].trim() };
  return { subject: null, body: text };
}

function formatReasons(raw) {
  if (!raw) return "";
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed.join(" · ");
  } catch {
    /* keep string */
  }
  return String(raw);
}

function pickShownDraft(drafts) {
  if (!drafts.length) return null;
  return [...drafts].reverse().find((d) => d.critic_verdict === "PASS") || drafts[drafts.length - 1];
}

function LogRow({ entry }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`receipt-row tone-${stepTone(entry)}`}>
      <button type="button" className="receipt-row-head" onClick={() => setOpen((v) => !v)}>
        <span className="receipt-dot" />
        <span className="receipt-step">{entry.step}</span>
        {entry.provider ? (
          <span className={`receipt-provider ${providerTone(entry.provider)}`}>{entry.provider}</span>
        ) : null}
        {entry.latency_ms != null ? <span className="receipt-ms">{entry.latency_ms}ms</span> : null}
        <span className="receipt-chevron">{open ? "−" : "+"}</span>
      </button>
      {entry.model ? <div className="receipt-model">{entry.model}</div> : null}
      {open ? (
        <div className="receipt-body">
          <div>
            <div className="receipt-k">input</div>
            <pre>{entry.input_summary || "—"}</pre>
          </div>
          <div>
            <div className="receipt-k">output</div>
            <pre>{entry.output || "—"}</pre>
          </div>
        </div>
      ) : null}
    </li>
  );
}

function DraftLetter({ draft, featured }) {
  const email = splitEmail(draft.body);
  const reasons = formatReasons(draft.critic_reasons);
  return (
    <article className={`receipt-letter ${featured ? "is-featured" : ""}`}>
      <div className="receipt-draft-meta">
        <span>Attempt {draft.attempt_number}</span>
        {draft.critic_verdict ? (
          <span className={`pill ${draft.critic_verdict === "PASS" ? "pass" : "fail"}`}>
            {draft.critic_verdict}
          </span>
        ) : null}
      </div>
      {email.subject ? <h4 className="receipt-subject">{email.subject}</h4> : null}
      <pre>{email.body}</pre>
      {reasons ? <div className="receipt-reasons">{reasons}</div> : null}
    </article>
  );
}

export default function RunReceipt({ detail, onClose, onReplied }) {
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [closer, setCloser] = useState(null);
  const [logOpen, setLogOpen] = useState(false);

  if (!detail) return null;
  const lead = detail.lead || {};
  const logs = detail.run_log || [];
  const drafts = detail.drafts || [];
  const replies = detail.replies || [];
  const shown = pickShownDraft(drafts);
  const earlier = drafts.filter((d) => d.id !== shown?.id);
  const canReply = ["SENT", "REPLIED", "APPROVED", "NURTURE", "MEETING_BOOKED"].includes(lead.stage);

  async function submitReply(event) {
    event.preventDefault();
    if (!reply.trim()) return;
    setBusy(true);
    setError("");
    try {
      const result = await simulateReply(lead.id, reply.trim());
      setCloser(result.closer || null);
      setReply("");
      onReplied?.(result);
    } catch (err) {
      setError(err.message || "reply failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="receipt" role="dialog" aria-label="Draft and run receipt">
      <header className="receipt-top">
        <div>
          <div className="receipt-handle">@{lead.github_handle}</div>
          <div className="receipt-project">
            {lead.project || lead.repo} · fit {lead.fit_score ?? "—"}
          </div>
        </div>
        <div className="receipt-top-right">
          <span className={`pill ${pillTone(lead.stage)}`}>{stageLabel(lead.stage)}</span>
          <button type="button" className="receipt-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
      </header>

      <section className="receipt-section receipt-drafts">
        <h3>Draft</h3>
        {shown ? (
          <DraftLetter draft={shown} featured />
        ) : (
          <p className="receipt-empty-note">No draft yet. This lead hasn’t reached the copywriter.</p>
        )}
        {earlier.length ? (
          <div className="receipt-earlier">
            <h3>Earlier attempts</h3>
            {earlier.map((draft) => (
              <DraftLetter key={draft.id} draft={draft} />
            ))}
          </div>
        ) : null}
      </section>

      {logs.length ? (
        <section className="receipt-section">
          <button type="button" className="receipt-log-toggle" onClick={() => setLogOpen((v) => !v)}>
            <h3>Run log</h3>
            <span>{logOpen ? "Hide" : "Show"} {logs.length} steps</span>
          </button>
          {logOpen ? (
            <ol className="receipt-log">
              {logs.map((entry) => (
                <LogRow key={entry.id} entry={entry} />
              ))}
            </ol>
          ) : null}
        </section>
      ) : null}

      {replies.length ? (
        <section className="receipt-section">
          <h3>Replies</h3>
          {replies.map((row) => (
            <article key={row.id} className="receipt-letter">
              <div className="receipt-draft-meta">
                <span>{row.category}</span>
              </div>
              <pre>{row.body}</pre>
            </article>
          ))}
        </section>
      ) : null}

      {closer ? (
        <section className="receipt-section">
          <h3>Handoff</h3>
          <pre>{JSON.stringify(closer, null, 2)}</pre>
        </section>
      ) : null}

      {canReply ? (
        <form className="receipt-reply" onSubmit={submitReply}>
          <label htmlFor="simulate-reply">Simulate reply</label>
          <textarea
            id="simulate-reply"
            rows={3}
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            placeholder="e.g. yeah that header thing is exactly it — can we talk Tuesday?"
          />
          {error ? <div className="receipt-error">{error}</div> : null}
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Classifying…" : "Classify reply"}
          </button>
        </form>
      ) : null}
    </aside>
  );
}
