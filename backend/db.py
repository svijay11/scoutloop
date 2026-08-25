from __future__ import annotations

import sqlite3
import json
import threading
from collections.abc import Callable
from typing import Any

from backend.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY,
  company_name TEXT,
  one_liner TEXT,
  problem TEXT,
  source_url TEXT,
  icp_summary TEXT,
  icp_signals_json TEXT,
  pain_points_json TEXT,
  competitors_json TEXT,
  positioning_angle TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY,
  github_handle TEXT,
  repo TEXT,
  name TEXT,
  email TEXT,
  project TEXT,
  stage TEXT DEFAULT 'NEW',
  fit_score INTEGER,
  campaign_id INTEGER REFERENCES campaigns(id),
  source_issue TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS briefs (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER REFERENCES leads(id),
  brief_json TEXT,
  raw_token_count INTEGER,
  brief_token_count INTEGER
);
CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER REFERENCES leads(id),
  attempt_number INTEGER,
  body TEXT,
  critic_verdict TEXT,
  critic_reasons TEXT
);
CREATE TABLE IF NOT EXISTS messages_sent (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER REFERENCES leads(id),
  draft_id INTEGER REFERENCES drafts(id),
  dry_run BOOLEAN,
  sent_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS replies (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER REFERENCES leads(id),
  body TEXT,
  category TEXT,
  received_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS run_log (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER,
  step TEXT,
  provider TEXT,
  model TEXT,
  latency_ms INTEGER,
  input_summary TEXT,
  output TEXT,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_run_log_lead ON run_log(lead_id);
CREATE INDEX IF NOT EXISTS idx_drafts_lead ON drafts(lead_id);
"""

_lock = threading.Lock()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = get_conn()
        try:
            conn.executescript(SCHEMA)
            _migrate(conn)
            conn.commit()
        finally:
            conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
          id INTEGER PRIMARY KEY,
          company_name TEXT,
          one_liner TEXT,
          problem TEXT,
          source_url TEXT,
          icp_summary TEXT,
          icp_signals_json TEXT,
          pain_points_json TEXT,
          competitors_json TEXT,
          positioning_angle TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}
    for name, ddl in (
        ("name", "TEXT"),
        ("email", "TEXT"),
        ("project", "TEXT"),
        ("campaign_id", "INTEGER REFERENCES campaigns(id)"),
        ("source_issue", "TEXT"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {name} {ddl}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_campaign ON leads(campaign_id)")
    camp_cols = {row["name"] for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()}
    if "problem" not in camp_cols:
        conn.execute("ALTER TABLE campaigns ADD COLUMN problem TEXT")


def _run(fn: Callable[[sqlite3.Connection], Any]) -> Any:
    with _lock:
        conn = get_conn()
        try:
            result = fn(conn)
            conn.commit()
            return result
        finally:
            conn.close()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def insert_lead(
    *,
    github_handle: str,
    repo: str,
    project: str | None = None,
    name: str | None = None,
    email: str | None = None,
    stage: str = "NEW",
    fit_score: int | None = None,
    campaign_id: int | None = None,
    source_issue: str | None = None,
) -> dict[str, Any]:
    def inner(conn: sqlite3.Connection) -> dict[str, Any]:
        cur = conn.execute(
            """
            INSERT INTO leads (
              github_handle, repo, project, name, email, stage, fit_score, campaign_id, source_issue
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (github_handle, repo, project, name, email, stage, fit_score, campaign_id, source_issue),
        )
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    return _run(inner)


def lead_exists(github_handle: str, repo: str, campaign_id: int | None = None) -> bool:
    def inner(conn: sqlite3.Connection) -> bool:
        if campaign_id is None:
            row = conn.execute(
                "SELECT id FROM leads WHERE github_handle = ? AND repo = ?",
                (github_handle, repo),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id FROM leads
                WHERE github_handle = ? AND repo = ? AND campaign_id = ?
                """,
                (github_handle, repo, campaign_id),
            ).fetchone()
        return row is not None

    return _run(inner)


def update_lead(lead_id: int, **fields: Any) -> dict[str, Any] | None:
    if not fields:
        return get_lead(lead_id)
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [lead_id]

    def inner(conn: sqlite3.Connection) -> dict[str, Any] | None:
        conn.execute(f"UPDATE leads SET {cols} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return _row(row)

    return _run(inner)


def list_leads() -> list[dict[str, Any]]:
    def inner(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    return _run(inner)


def get_lead(lead_id: int) -> dict[str, Any] | None:
    def inner(conn: sqlite3.Connection) -> dict[str, Any] | None:
        return _row(conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())

    return _run(inner)


def insert_brief(
    lead_id: int,
    brief_json: str,
    raw_token_count: int,
    brief_token_count: int,
) -> dict[str, Any]:
    def inner(conn: sqlite3.Connection) -> dict[str, Any]:
        cur = conn.execute(
            """
            INSERT INTO briefs (lead_id, brief_json, raw_token_count, brief_token_count)
            VALUES (?, ?, ?, ?)
            """,
            (lead_id, brief_json, raw_token_count, brief_token_count),
        )
        row = conn.execute("SELECT * FROM briefs WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    return _run(inner)


def briefs_for_lead(lead_id: int) -> list[dict[str, Any]]:
    def inner(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM briefs WHERE lead_id = ? ORDER BY id ASC", (lead_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    return _run(inner)


def update_latest_brief(lead_id: int, brief_json: str, brief_token_count: int | None = None) -> dict[str, Any] | None:
    def inner(conn: sqlite3.Connection) -> dict[str, Any] | None:
        row = conn.execute(
            "SELECT * FROM briefs WHERE lead_id = ? ORDER BY id DESC LIMIT 1",
            (lead_id,),
        ).fetchone()
        if row is None:
            return None
        if brief_token_count is None:
            conn.execute("UPDATE briefs SET brief_json = ? WHERE id = ?", (brief_json, row["id"]))
        else:
            conn.execute(
                "UPDATE briefs SET brief_json = ?, brief_token_count = ? WHERE id = ?",
                (brief_json, brief_token_count, row["id"]),
            )
        return _row(conn.execute("SELECT * FROM briefs WHERE id = ?", (row["id"],)).fetchone())

    return _run(inner)


def insert_draft(
    lead_id: int,
    attempt_number: int,
    body: str,
    critic_verdict: str | None = None,
    critic_reasons: str | None = None,
) -> dict[str, Any]:
    def inner(conn: sqlite3.Connection) -> dict[str, Any]:
        cur = conn.execute(
            """
            INSERT INTO drafts (lead_id, attempt_number, body, critic_verdict, critic_reasons)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lead_id, attempt_number, body, critic_verdict, critic_reasons),
        )
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    return _run(inner)


def update_draft(draft_id: int, **fields: Any) -> dict[str, Any] | None:
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [draft_id]

    def inner(conn: sqlite3.Connection) -> dict[str, Any] | None:
        conn.execute(f"UPDATE drafts SET {cols} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        return _row(row)

    return _run(inner)


def drafts_for_lead(lead_id: int) -> list[dict[str, Any]]:
    def inner(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM drafts WHERE lead_id = ? ORDER BY attempt_number ASC, id ASC",
            (lead_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    return _run(inner)


def insert_message_sent(lead_id: int, draft_id: int, dry_run: bool) -> dict[str, Any]:
    def inner(conn: sqlite3.Connection) -> dict[str, Any]:
        cur = conn.execute(
            "INSERT INTO messages_sent (lead_id, draft_id, dry_run) VALUES (?, ?, ?)",
            (lead_id, draft_id, 1 if dry_run else 0),
        )
        row = conn.execute("SELECT * FROM messages_sent WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    return _run(inner)


def messages_for_lead(lead_id: int) -> list[dict[str, Any]]:
    def inner(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM messages_sent WHERE lead_id = ? ORDER BY id ASC", (lead_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    return _run(inner)


def insert_reply(lead_id: int, body: str, category: str) -> dict[str, Any]:
    def inner(conn: sqlite3.Connection) -> dict[str, Any]:
        cur = conn.execute(
            "INSERT INTO replies (lead_id, body, category) VALUES (?, ?, ?)",
            (lead_id, body, category),
        )
        row = conn.execute("SELECT * FROM replies WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    return _run(inner)


def replies_for_lead(lead_id: int) -> list[dict[str, Any]]:
    def inner(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM replies WHERE lead_id = ? ORDER BY id ASC", (lead_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    return _run(inner)


def insert_run_log(
    *,
    lead_id: int | None,
    step: str,
    provider: str | None,
    model: str | None,
    latency_ms: int | None,
    input_summary: str | None,
    output: str | None,
) -> dict[str, Any]:
    def inner(conn: sqlite3.Connection) -> dict[str, Any]:
        cur = conn.execute(
            """
            INSERT INTO run_log (lead_id, step, provider, model, latency_ms, input_summary, output)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (lead_id, step, provider, model, latency_ms, input_summary, output),
        )
        row = conn.execute("SELECT * FROM run_log WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    return _run(inner)


def run_log_for_lead(lead_id: int) -> list[dict[str, Any]]:
    def inner(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM run_log WHERE lead_id = ? ORDER BY id ASC", (lead_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    return _run(inner)


def count_leads_created_today() -> int:
    """Live leads that already spent an LLM compressor call today.

    Demo rows and scout-only inserts do not count — they never billed Groq/OpenRouter.
    """

    def inner(conn: sqlite3.Connection) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM leads
            WHERE date(created_at) = date('now')
              AND campaign_id IS NOT NULL
              AND id IN (SELECT lead_id FROM run_log WHERE step = 'compressor')
            """
        ).fetchone()
        return int(row["n"]) if row else 0

    return _run(inner)


def compression_stats() -> dict[str, int]:
    def inner(conn: sqlite3.Connection) -> dict[str, int]:
        row = conn.execute(
            """
            SELECT
              COALESCE(SUM(raw_token_count), 0) AS raw_tokens,
              COALESCE(SUM(brief_token_count), 0) AS brief_tokens,
              COUNT(*) AS brief_count
            FROM briefs
            """
        ).fetchone()
        return {
            "raw_tokens": int(row["raw_tokens"]),
            "brief_tokens": int(row["brief_tokens"]),
            "brief_count": int(row["brief_count"]),
        }

    return _run(inner)


def serialize_campaign(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None

    def _load(raw: Any, fallback: Any) -> Any:
        if raw in (None, ""):
            return fallback
        if not isinstance(raw, str):
            return raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return fallback

    out = dict(row)
    out["icp_signals"] = _load(
        row.get("icp_signals_json"),
        {"dependencies": [], "topics": [], "keywords": []},
    )
    out["pain_points"] = _load(row.get("pain_points_json"), [])
    out["competitors"] = normalize_competitors(_load(row.get("competitors_json"), []))
    out["problem"] = str(
        row.get("problem") or row.get("one_liner") or row.get("icp_summary") or ""
    ).strip()
    return out


def normalize_competitors(raw: Any) -> list[dict[str, str]]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = [raw] if raw.strip() else []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            url = str(item.get("source_url") or item.get("url") or "").strip()
        else:
            name = str(item).strip()
            url = ""
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "source_url": url})
    return out


def competitor_names(raw: Any) -> list[str]:
    return [item["name"] for item in normalize_competitors(raw)]


def insert_campaign(
    *,
    company_name: str | None,
    one_liner: str | None,
    source_url: str | None,
    icp_summary: str,
    icp_signals_json: str,
    pain_points_json: str,
    competitors_json: str,
    positioning_angle: str,
    problem: str | None = None,
) -> dict[str, Any]:
    problem_text = (problem or one_liner or icp_summary or "").strip()

    def inner(conn: sqlite3.Connection) -> dict[str, Any]:
        cur = conn.execute(
            """
            INSERT INTO campaigns (
              company_name, one_liner, problem, source_url, icp_summary,
              icp_signals_json, pain_points_json, competitors_json, positioning_angle
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name,
                one_liner or problem_text,
                problem_text,
                source_url,
                icp_summary,
                icp_signals_json,
                pain_points_json,
                competitors_json,
                positioning_angle,
            ),
        )
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    return _run(inner)


def insert_problem(problem: str) -> dict[str, Any]:
    text = problem.strip()
    if not text:
        raise ValueError("problem is required")
    return insert_campaign(
        company_name=None,
        one_liner=text,
        source_url=None,
        icp_summary=text,
        icp_signals_json="{}",
        pain_points_json="[]",
        competitors_json="[]",
        positioning_angle="",
        problem=text,
    )


def get_campaign(campaign_id: int) -> dict[str, Any] | None:
    def inner(conn: sqlite3.Connection) -> dict[str, Any] | None:
        return _row(
            conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        )

    return _run(inner)


def campaign_for_lead(lead: dict[str, Any] | None) -> dict[str, Any] | None:
    if not lead or not lead.get("campaign_id"):
        return None
    return serialize_campaign(get_campaign(int(lead["campaign_id"])))


def list_campaigns() -> list[dict[str, Any]]:
    def inner(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute("SELECT * FROM campaigns ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    return _run(inner)
