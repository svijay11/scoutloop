from __future__ import annotations

import json
from contextlib import asynccontextmanager

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

NO_STORE = {"Cache-Control": "no-store, max-age=0"}


def _index_page() -> FileResponse | JSONResponse:
    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index, headers=NO_STORE)
    return JSONResponse(
        {
            "service": "scoutloop",
            "hint": "frontend not built — run scoutloop serve or npm run build in frontend/",
        }
    )
from pydantic import BaseModel, Field

from backend import db
from backend.config import FRONTEND_DIST, get_send_mode, set_send_mode, smtp_config
from backend.orchestrator import handle_reply, run_pipeline
from backend.providers import budget_snapshot


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Scoutloop", docs_url="/api/docs", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8787"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    problem: Optional[str] = None
    campaign_id: Optional[int] = None
    limit: int = Field(default=10, ge=1, le=50)
    demo: bool = False


class ReplyRequest(BaseModel):
    body: str = Field(min_length=1)


class SettingsRequest(BaseModel):
    send_mode: str


def _lead_detail(lead_id: int) -> dict:
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    return {
        "lead": lead,
        "briefs": db.briefs_for_lead(lead_id),
        "drafts": db.drafts_for_lead(lead_id),
        "messages_sent": db.messages_for_lead(lead_id),
        "replies": db.replies_for_lead(lead_id),
        "run_log": db.run_log_for_lead(lead_id),
    }


@app.get("/api/leads")
def api_leads() -> dict:
    return {"leads": db.list_leads()}


@app.get("/api/leads/{lead_id}")
def api_lead(lead_id: int) -> dict:
    return _lead_detail(lead_id)


@app.get("/api/campaigns")
def api_list_campaigns() -> dict:
    return {"campaigns": [db.serialize_campaign(row) for row in db.list_campaigns()]}


@app.get("/api/campaigns/{campaign_id}")
def api_get_campaign(campaign_id: int) -> dict:
    row = db.serialize_campaign(db.get_campaign(campaign_id))
    if not row:
        raise HTTPException(404, "campaign not found")
    return {"campaign": row}


@app.post("/api/run")
async def api_run(req: RunRequest) -> StreamingResponse:
    async def events():
        try:
            async for event in run_pipeline(
                req.limit,
                campaign_id=req.campaign_id,
                problem=req.problem,
                demo=req.demo,
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:  # noqa: BLE001 — surface pipeline errors on the stream
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'count': 0})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/leads/{lead_id}/reply")
async def api_reply(lead_id: int, req: ReplyRequest) -> dict:
    try:
        return await handle_reply(lead_id, req.body)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/budget")
def api_budget() -> dict:
    return budget_snapshot()


@app.get("/api/stats")
def api_stats() -> dict:
    stats = db.compression_stats()
    raw = stats["raw_tokens"]
    brief = stats["brief_tokens"]
    saved = 0
    if raw > 0:
        saved = round((1 - (brief / raw)) * 100)
    return {**stats, "saved_pct": max(0, saved)}


@app.get("/api/settings")
def api_settings() -> dict:
    return {"send_mode": get_send_mode()}


@app.post("/api/settings")
def api_set_settings(req: SettingsRequest) -> dict:
    mode = req.send_mode if req.send_mode == "live" else "dry_run"
    if mode == "live":
        smtp = smtp_config()
        if not smtp["host"] or not smtp["from_addr"]:
            raise HTTPException(
                400,
                "live mode needs SMTP_HOST and SMTP_FROM in .env — send stays dry_run otherwise",
            )
    return {"send_mode": set_send_mode(mode)}


@app.get("/")
def landing():
    return _index_page()


@app.get("/{path:path}")
def spa(path: str):
    if path.startswith("api/") or path == "api":
        raise HTTPException(404)
    candidate = FRONTEND_DIST / path
    if candidate.is_file():
        return FileResponse(candidate)
    return _index_page()
