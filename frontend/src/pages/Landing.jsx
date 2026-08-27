import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { FALLBACK_STATS } from "../demoData.js";
import { fetchStats } from "../api.js";
import BlurText from "../components/BlurText.jsx";
import useLandingMotion, { useLandingBodyClass } from "../landing/useLandingMotion.js";
import "../styles/landing.css";

const SCAN = [
  { id: "gh", label: "Finding people talking about the problem" },
  { id: "issue", label: "Reading their issues and READMEs" },
  { id: "model", label: "Searching Tavily for a solution" },
];

const PANELS = [
  {
    tone: "blue",
    title: "The critic closes the gap.",
    body: "Every draft is checked before it sends — fabricated claims, spam triggers, and generic filler get sent back for a rewrite, not shipped.",
  },
  {
    tone: "green",
    title: "Compression before the agent sees anything.",
    body: "Raw READMEs and issue threads get collapsed into a ~200-token brief before drafting starts.",
  },
  {
    tone: "yellow",
    title: "Every run leaves a receipt.",
    body: "Full trace from raw research to sent message, stored and inspectable, not thrown away.",
  },
];

const ACCORDION = [
  {
    title: "Capture every public signal",
    body: "Scout GitHub for people already talking about the problem, pull the README, recent issues, and commits, and keep only what a public profile actually exposes — never post in their issues.",
  },
  {
    title: "Trace every claim to the brief",
    body: "The critic refuses to ship a sentence that isn't grounded in the compressed brief. Failures go back to the copywriter, up to a hard retry cap, then park for a human.",
  },
  {
    title: "Meet the stack where it already is",
    body: "Tavily is used after research, to propose a solution for that lead's pain. Groq and OpenRouter run as a pair with automatic failover. A 429 on one provider never stalls the loop.",
  },
  {
    title: "Built for a loop you can inspect",
    body: "Dry-run is the default. Live send is an explicit flag plus a confirm. Every lead leaves a receipt you can open on the board.",
  },
];

const FAQ = [
  {
    q: "How does Scoutloop strengthen outbound?",
    a: "You state a problem. It finds people already talking about it on GitHub, researches the repo, looks up a solution on Tavily, then drafts an email that has to name that pain.",
  },
  {
    q: "How do we ensure draft quality?",
    a: "Rule checks catch spam triggers, length, jargon, and a missing opt-out. An LLM critic catches invented facts. Both have to pass.",
  },
  {
    q: "How does it fit the existing stack?",
    a: "GitHub to find and research people with the problem, Tavily to propose a solution, Groq and OpenRouter for the LLM steps, SMTP only if you flip SEND_MODE=live. It runs on your laptop.",
  },
  {
    q: "How does this add traceability?",
    a: "Every step writes to run_log. Click a card on the dashboard and you get the receipt: provider, model, latency, input, output.",
  },
];

function Mark() {
  return (
    <span className="df-mark" aria-hidden="true">
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

export default function Landing() {
  const root = useRef(null);
  const [stats, setStats] = useState(FALLBACK_STATS);
  const [faq, setFaq] = useState(0);
  useLandingBodyClass();
  useLandingMotion(root);

  useEffect(() => {
    fetchStats()
      .then((data) => {
        if (data.brief_count > 0 && data.raw_tokens > 0) setStats(data);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="df" ref={root}>
      <header className="df-nav">
        <Link to="/" className="df-brand">
          <Mark />
          Scoutloop
        </Link>
        <div className="df-nav-cluster">
          <nav className="df-nav-pill">
            <Link to="/">Home</Link>
            <Link to="/dashboard">Dashboard</Link>
            <span>Loop</span>
          </nav>
          <Link to="/dashboard" className="df-nav-cta">
            Run the loop
          </Link>
        </div>
      </header>

      <section className="df-hero">
        <h1 className="df-hero-title">
          <BlurText
            as="span"
            text="The outbound agent for developer tools"
            delay={200}
            animateBy="words"
            direction="top"
            stepDuration={0.45}
            className="df-hero-blur"
          />
        </h1>
        <p className="df-hero-sub">
          Scoutloop finds GitHub developers who are already hitting a problem, researches the
          repo, looks up a solution, and drafts an email the critic will actually sign.
        </p>
        <div className="df-hero-cta">
          <Link to="/dashboard" className="df-btn-green">
            Run the loop
          </Link>
          <Link to="/dashboard" className="df-text-link">
            Open the dashboard
          </Link>
        </div>

        <div className="df-hero-stage">
          <div className="df-hero-card">
            <header className="df-desk-bar">
              <strong>token-shepherd</strong>
              <div className="df-chips">
                <span>Properties</span>
                <span>Discovery</span>
                <span>Nivedita</span>
                <span className="hi">High</span>
              </div>
            </header>

            <div className="df-work">
              <div className="df-type-wrap">
                <div className="df-type-box">
                  <span
                    className="df-typed"
                    data-type="find the risks in this repo before outreach"
                  />
                  <span className="df-caret">|</span>
                </div>
              </div>

              <ul className="df-scan">
                {SCAN.map((row) => (
                  <li className={`df-scan-row df-scan-${row.id}`} key={row.id}>
                    <span className="df-scan-ico" />
                    {row.label}
                  </li>
                ))}
              </ul>

              <div className="df-skel" aria-hidden="true">
                <span style={{ width: "92%" }} />
                <span style={{ width: "78%" }} />
                <span style={{ width: "86%" }} />
                <span style={{ width: "64%" }} />
                <span style={{ width: "88%" }} />
                <span style={{ width: "71%" }} />
                <span style={{ width: "81%" }} />
                <span style={{ width: "54%" }} />
              </div>

              <p className="df-insight">
                Found a contradiction in the brief: the draft claims a 10x throughput win, but issue
                #128 only describes embedding-batch jobs dying at the Groq token cap. The critic sent
                it back. Next pass has to name that pain, not invent a metric.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="df-gap df-reveal">
        <h2 className="df-section-title">
          Cold outreach fails in the gaps. Scoutloop closes them.
        </h2>
        <div className="df-panels">
          {PANELS.map((panel) => (
            <article className={`df-panel df-panel-${panel.tone}`} key={panel.title}>
              <div className="df-panel-art">
                {panel.tone === "blue" ? <PanelLeads /> : null}
                {panel.tone === "green" ? (
                  <PanelDoc
                    raw={stats.raw_tokens}
                    brief={stats.brief_tokens}
                    saved={stats.saved_pct}
                  />
                ) : null}
                {panel.tone === "yellow" ? <PanelStack /> : null}
              </div>
              <h3>{panel.title}</h3>
              <p>{panel.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="df-split">
        <div className="df-split-art" aria-hidden="true">
          <StackOrbit />
        </div>
        <div className="df-split-copy">
          <p className="df-kicker">Agents that know the loop</p>
          <h2>Your partner for outbound that leaves a receipt.</h2>
          <div className="df-acc">
            {ACCORDION.map((item) => (
              <div className="df-acc-item" key={item.title}>
                <button type="button" className="df-acc-head">
                  <span>{item.title}</span>
                  <i />
                </button>
                <div className="df-acc-body">
                  <div>
                    <p>{item.body}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="df-manifesto">
        <p>
          For years, cold outreach has lived in a spreadsheet, a scraped list, or a template nobody
          personalized. Every sequence started from scratch. Every email reinvented the pitch.
        </p>
        <p>That era is over.</p>
        <p>
          Outbound in the next decade will be won by the teams that research before they write,
          compress before they draft, and refuse to send anything a critic wouldn't sign.
        </p>
        <p>Scoutloop is building that loop.</p>
      </section>

      <section className="df-local df-reveal">
        <p className="df-kicker">Built to run on your machine</p>
        <h2>No accounts. No tenants. Keys stay local.</h2>
        <div className="df-local-grid">
          <article>
            <h3>Your data, your control</h3>
            <p>SQLite on disk. API keys in a local .env. Nothing is hosted, because there are no other users.</p>
          </article>
          <article>
            <h3>Dry-run until you say otherwise</h3>
            <p>SEND_MODE defaults to dry_run. Live SMTP needs the env flag, SMTP credentials, and a confirm.</p>
          </article>
          <article>
            <h3>No public posting</h3>
            <p>Outreach goes to a public email on a profile. Scoutloop never comments on issues, PRs, or discussions.</p>
          </article>
        </div>
      </section>

      <section className="df-faq df-reveal">
        <h2>Questions &amp; Answers</h2>
        <div>
          {FAQ.map((item, i) => (
            <div className={`df-faq-item${faq === i ? " is-open" : ""}`} key={item.q}>
              <button type="button" onClick={() => setFaq(faq === i ? -1 : i)}>
                {item.q}
                <i />
              </button>
              <div className="df-acc-body">
                <div>
                  <p>{item.a}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="df-close df-reveal">
        <h2 className="df-close-title">A new standard for developer-tool outbound.</h2>
        <p>Discover how Scoutloop researches, compresses, drafts, and checks — then leaves the receipt.</p>
        <Link to="/dashboard" className="df-btn-green">
          Run the loop
        </Link>
      </section>

      <footer className="df-foot">
        <span>
          <Mark /> Scoutloop
        </span>
        <span>Outbound that leaves a receipt.</span>
      </footer>
    </div>
  );
}

function IconGitHub() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

function IconClaude() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 1.4 14.1 9.9 22.6 12 14.1 14.1 12 22.6 9.9 14.1 1.4 12 9.9 9.9z"
      />
    </svg>
  );
}

function IconGpt() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.127a5.9847 5.9847 0 0 0-3.5258 2.9 6.0462 6.0462 0 0 0 .7428 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-5.8492 6.0557 6.0557 0 0 0-1.2266-3.1231 5.96 5.96 0 0 0 .277-1.0003zM13.2599 22.4008a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.677-3.2482a4.4364 4.4364 0 0 1-.5343-3.0137l.142.0852 4.783 2.7616a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.5 4.5 0 0 1-6.1571-.7976zM2.3408 7.8956a4.4793 4.4793 0 0 1 2.3497-1.9738V11.6a.7661.7661 0 0 0 .3882.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.8956zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.127-3.0784-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.499 4.499 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.499 4.499 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654c.6458-.3725 1.3543-.3725 2.0001 0l4.7783 2.7582a.0941.0941 0 0 1 0 .1634l-4.7784 2.7582a1.826 1.826 0 0 1-2.0001 0L6.6259 12.661a.0941.0941 0 0 1 0-.1634z"
      />
    </svg>
  );
}

function StackOrbit() {
  return (
    <div className="df-orbit">
      <i className="df-orbit-ring r1" />
      <i className="df-orbit-ring r2" />
      <i className="df-orbit-ring r3" />
      <i className="df-orbit-pulse" />
      <i className="df-orbit-pulse is-late" />
      <div className="df-orbit-hub">
        <span className="df-mark">
          <i className="g" />
          <i />
          <i className="o" />
          <i />
          <i className="g" />
          <i />
          <i className="o" />
          <i />
          <i className="g" />
        </span>
      </div>
      <div className="df-orbit-track is-outer" style={{ "--dur": "34s" }}>
        <div className="df-orbit-pos" style={{ "--a": "0deg" }}>
          <div className="df-orbit-slot">
            <div className="df-orbit-chip is-github" title="GitHub">
              <span className="df-orbit-face">
                <IconGitHub />
              </span>
            </div>
          </div>
        </div>
        <div className="df-orbit-pos" style={{ "--a": "120deg" }}>
          <div className="df-orbit-slot">
            <div className="df-orbit-chip is-claude" title="Claude">
              <span className="df-orbit-face">
                <IconClaude />
              </span>
            </div>
          </div>
        </div>
        <div className="df-orbit-pos" style={{ "--a": "240deg" }}>
          <div className="df-orbit-slot">
            <div className="df-orbit-chip is-gpt" title="GPT">
              <span className="df-orbit-face">
                <IconGpt />
              </span>
            </div>
          </div>
        </div>
      </div>
      <div className="df-orbit-track is-inner is-rev" style={{ "--dur": "22s" }}>
        <div className="df-orbit-pos" style={{ "--a": "40deg" }}>
          <div className="df-orbit-slot">
            <div className="df-orbit-chip is-sm is-claude" title="Claude">
              <span className="df-orbit-face">
                <IconClaude />
              </span>
            </div>
          </div>
        </div>
        <div className="df-orbit-pos" style={{ "--a": "160deg" }}>
          <div className="df-orbit-slot">
            <div className="df-orbit-chip is-sm is-gpt" title="GPT">
              <span className="df-orbit-face">
                <IconGpt />
              </span>
            </div>
          </div>
        </div>
        <div className="df-orbit-pos" style={{ "--a": "280deg" }}>
          <div className="df-orbit-slot">
            <div className="df-orbit-chip is-sm is-github" title="GitHub">
              <span className="df-orbit-face">
                <IconGitHub />
              </span>
            </div>
          </div>
        </div>
      </div>
      <div className="df-orbit-track is-sparks" style={{ "--dur": "16s" }}>
        {["18deg", "108deg", "198deg", "288deg"].map((angle) => (
          <div className="df-orbit-pos" style={{ "--a": angle }} key={angle}>
            <i className="df-orbit-spark" />
          </div>
        ))}
      </div>
    </div>
  );
}

function PanelLeads() {
  return (
    <div className="df-mock-list">
      <header>
        <span>token-shepherd</span>
        <b>86</b>
      </header>
      {["QUALIFIED · window-saw", "DRAFTED · tool-loop", "SENT · token-shepherd"].map((row) => (
        <div key={row}>{row}</div>
      ))}
    </div>
  );
}

function PanelDoc({ raw, brief, saved }) {
  return (
    <div className="df-mock-doc">
      <div>Research dump</div>
      <p>
        {Number(raw).toLocaleString("en-US")} tokens → {Number(brief).toLocaleString("en-US")} ·{" "}
        {saved}% saved
      </p>
      <span />
      <span />
      <span />
    </div>
  );
}

function PanelStack() {
  return (
    <div className="df-mock-stack">
      <article>
        <em>Receipt</em>
        <strong>critic · FAIL → PASS</strong>
      </article>
      <article>
        <em>Handoff</em>
        <strong>Tue 10:00 or Thu 14:00</strong>
      </article>
    </div>
  );
}
