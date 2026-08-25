import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Board from "../components/Board.jsx";
import BudgetBar from "../components/BudgetBar.jsx";
import RunReceipt from "../components/RunReceipt.jsx";
import { DRAFT_STAGES } from "../stages.js";
import {
  fetchBudget,
  fetchCampaigns,
  fetchLead,
  fetchLeads,
  fetchSettings,
  runPipeline,
  setSendMode,
} from "../api.js";
import "../styles/dashboard.css";

function Mark() {
  return (
    <span className="dash-mark" aria-hidden="true">
      <i className="g" />
      <i />
      <i className="g" />
      <i />
      <i className="o" />
      <i />
      <i className="g" />
      <i />
      <i className="o" />
    </span>
  );
}

export default function Dashboard() {
  const [leads, setLeads] = useState([]);
  const [budget, setBudget] = useState(null);
  const [sendMode, setSendModeState] = useState("dry_run");
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [problem, setProblem] = useState("");
  const seededProblem = useRef(false);
  const [limit, setLimit] = useState(3);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [toggling, setToggling] = useState(false);
  const [ready, setReady] = useState(false);
  const [runLeadIds, setRunLeadIds] = useState(null);
  const [thoughts, setThoughts] = useState([]);
  const areaRef = useRef(null);
  const seenLeads = useRef([]);
  const thoughtTick = useRef(0);
  const showBoard = runLeadIds != null;
  const visibleLeads = showBoard ? leads.filter((lead) => runLeadIds.includes(lead.id)) : [];
  const idle = ready && !showBoard;

  const refresh = useCallback(async () => {
    const [leadData, budgetData, settings, campaignData] = await Promise.all([
      fetchLeads(),
      fetchBudget(),
      fetchSettings(),
      fetchCampaigns().catch(() => ({ campaigns: [] })),
    ]);
    setLeads(leadData.leads || []);
    setBudget(budgetData);
    setSendModeState(settings.send_mode || "dry_run");
    const nextCampaigns = campaignData.campaigns || [];
    if (!seededProblem.current && nextCampaigns[0]?.problem) {
      seededProblem.current = true;
      setProblem(nextCampaigns[0].problem);
    }
  }, []);

  useLayoutEffect(() => {
    document.documentElement.classList.remove("is-landing");
    document.body.classList.remove("is-landing");
    document.documentElement.classList.add("is-dash");
    document.body.classList.add("is-dash");
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    window.scrollTo(0, 0);
    return () => {
      document.documentElement.classList.remove("is-dash");
      document.body.classList.remove("is-dash");
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
    };
  }, []);

  useEffect(() => {
    refresh()
      .catch((err) => setError(err.message))
      .finally(() => setReady(true));
  }, [refresh]);

  useEffect(() => {
    if (selectedId == null) {
      setDetail(null);
      return;
    }
    fetchLead(selectedId)
      .then(setDetail)
      .catch((err) => setError(err.message));
  }, [selectedId, leads]);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") setSelectedId(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [problem, showBoard]);

  useEffect(() => {
    if (idle) areaRef.current?.focus();
  }, [idle]);

  async function startRun(demo) {
    setRunning(true);
    setError("");
    setRunLeadIds([]);
    setSelectedId(null);
    seenLeads.current = [];
    thoughtTick.current = 0;
    setThoughts([]);
    setStatus(demo ? "Starting…" : "Starting…");
    try {
      await runPipeline({
        problem: demo ? null : problem.trim(),
        limit: Number(limit) || 3,
        demo,
        onEvent: (event) => {
          if (event.type === "status" && event.message) {
            setStatus(event.message);
            const id = (thoughtTick.current += 1);
            setThoughts((prev) => [...prev, { id, text: event.message }].slice(-6));
            return;
          }
          if (event.type === "scouted") {
            setStatus(`Found ${event.count} people talking about it`);
          }
          if (event.type === "lead") {
            const id = event.lead?.id;
            if (id != null) {
              setRunLeadIds((prev) => (prev?.includes(id) ? prev : [...(prev || []), id]));
              seenLeads.current = seenLeads.current.filter((row) => row.id !== id);
              seenLeads.current.push(event.lead);
            }
          }
          if (event.type === "error") setError(event.message);
          if (event.type === "done") {
            const pick = seenLeads.current.find((row) => DRAFT_STAGES.has(row.stage));
            if (pick?.id) setSelectedId(pick.id);
          }
          refresh().catch(() => {});
        },
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
      refresh().catch(() => {});
    }
  }

  async function onToggleSend(next) {
    if (next === "live") {
      const ok = window.confirm(
        "Flip SEND_MODE to live? Messages will be delivered over SMTP. This is not a dry run."
      );
      if (!ok) return;
    }
    setToggling(true);
    try {
      const result = await setSendMode(next);
      setSendModeState(result.send_mode);
    } catch (err) {
      setError(err.message);
    } finally {
      setToggling(false);
    }
  }

  return (
    <div
      className={`dash ${!ready ? "is-booting" : idle ? "is-idle" : "has-run"}${
        visibleLeads.length ? " has-board" : ""
      }${detail ? " has-receipt" : ""}`}
    >
      <div className="dash-sky" aria-hidden="true" />

      <header className="dash-nav">
        <Link to="/" className="dash-brand">
          <Mark />
          Scoutloop
        </Link>
        <BudgetBar
          budget={budget}
          sendMode={sendMode}
          onToggleSend={onToggleSend}
          toggling={toggling}
        />
      </header>

      <div className="dash-stage">
        <div className="dash-work">
          {running || thoughts.length ? (
            <div className="dash-think" aria-live="polite">
              {thoughts.slice(-4).map((thought, index, list) => {
                const current = running && index === list.length - 1;
                return (
                  <p key={thought.id} className={current ? "is-now" : "is-past"}>
                    {thought.text}
                    {current ? (
                      <span className="dash-think-dots" aria-hidden="true">
                        <i />
                        <i />
                        <i />
                      </span>
                    ) : null}
                  </p>
                );
              })}
            </div>
          ) : null}

          <div className="dash-dock">
          {idle ? <p className="dash-kicker">State a problem people are already hitting</p> : null}
          <form
            className="dash-composer"
            onSubmit={(e) => {
              e.preventDefault();
              if (!problem.trim()) {
                setError("explain the problem first");
                return;
              }
              startRun(false);
            }}
          >
          <label className="dash-problem">
            <span className="dash-sr">Problem</span>
            <textarea
              ref={areaRef}
              rows={1}
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                  e.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="e.g. Modal GPU jobs die at the 24h preempt and resume with a stale tokenizer"
            />
          </label>
          <div className="dash-composer-bar">
            <label className="dash-limit">
              <span>Limit</span>
              <input
                type="number"
                min={1}
                max={20}
                value={limit}
                onChange={(e) => setLimit(e.target.value)}
              />
            </label>
            <p className="dash-status" aria-live="polite">
              {status}
              {error ? <span className="dash-error">{error}</span> : null}
            </p>
            <button className="dash-text-btn" type="button" disabled={running} onClick={() => startRun(true)}>
              Demo run
            </button>
            <button className="dash-run-btn" type="submit" disabled={running}>
              {running ? "Running…" : "Run the loop"}
            </button>
          </div>
        </form>
          </div>

          {visibleLeads.length ? (
            <div className="dash-board">
              <Board leads={visibleLeads} selectedId={selectedId} onSelect={setSelectedId} />
            </div>
          ) : null}
        </div>
      </div>

      {detail ? (
        <RunReceipt
          detail={detail}
          onClose={() => setSelectedId(null)}
          onReplied={() => refresh()}
        />
      ) : null}
    </div>
  );
}
