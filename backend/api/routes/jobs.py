"""
Job queue — live search (Remotive + Arbeitnow) + manual JD paste.
All data is persisted per-user in Supabase (jobs, apply_clicks, applications tables).
"""

import html
import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from backend.parsers.jd_parser import parse_jd
from backend.parsers.schemas import JobDescription
from backend.auth_deps import get_current_user_id
from backend.db import get_db

router = APIRouter()


def _strip_html(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Request / response models ─────────────────────────────────


class JDInput(BaseModel):
    jd_text: str
    source_url: str = ""


class JobSearchRequest(BaseModel):
    query: str
    location: str = ""
    resume_id: str = ""
    remote_only: bool = False
    date_posted: str = "week"
    max_results: int = 20


class StatusUpdate(BaseModel):
    status: str  # submitted | phone_screen | interviewing | offer | rejected


# ── Helpers ───────────────────────────────────────────────────


def _jd_to_row(jd: JobDescription, user_id: str) -> dict:
    return {
        "id": jd.id,
        "user_id": user_id,
        "data": jd.model_dump(mode="json"),
        "source_url": jd.source_url or None,
    }


def _row_to_jd(row: dict) -> JobDescription:
    return JobDescription(**row["data"])


# ── Queue endpoints ───────────────────────────────────────────


@router.get("/queue")
async def get_job_queue(user_id: str = Depends(get_current_user_id)):
    db = get_db()
    resp = db.table("jobs").select("data").eq("user_id", user_id).order("created_at", desc=True).execute()
    return [r["data"] for r in resp.data]


@router.post("/jd", response_model=JobDescription)
async def paste_jd(input: JDInput, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    jd = parse_jd(input.jd_text, source="manual", source_url=input.source_url)
    db.table("jobs").upsert(_jd_to_row(jd, user_id)).execute()
    return jd


@router.post("/search")
async def search_live_jobs(
    request: JobSearchRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_db()

    # Get URLs already seen by this user to dedup
    seen_resp = db.table("jobs").select("source_url").eq("user_id", user_id).execute()
    seen_urls: set[str] = {r["source_url"] for r in seen_resp.data if r["source_url"]}

    resume = None
    if request.resume_id:
        try:
            from backend.api.routes.resume import _resume_store
            resume = _resume_store.get(request.resume_id)
        except Exception:
            pass

    try:
        from backend.agents.scout.scrapers.remotive import RemotiveScraper
        from backend.agents.scout.scrapers.arbeitnow import ArbeitnowScraper

        half = max(request.max_results // 2, 10)
        remotive_jobs = await RemotiveScraper().search(request.query, max_results=half)
        arbeitnow_jobs = await ArbeitnowScraper().search(
            request.query, request.location, max_results=half
        )
        scraped = (remotive_jobs + arbeitnow_jobs)[: request.max_results]

        jobs_out = []
        rows = []
        for s in scraped:
            if s.url and s.url in seen_urls:
                continue
            jd = parse_jd(_strip_html(s.description), source=s.source, source_url=s.url)
            if s.title:   jd.title = s.title
            if s.company: jd.company = s.company
            if s.location: jd.location = s.location
            if s.remote_policy: jd.remote_policy = s.remote_policy
            if s.salary_text: jd.salary_range = s.salary_text
            if s.url: jd.source_url = s.url

            if resume:
                from backend.agents.scout.scorer import score_fit_ai
                fit = await score_fit_ai(resume, jd)
                jd.fit_score = fit.total_score

            rows.append(_jd_to_row(jd, user_id))
            if s.url:
                seen_urls.add(s.url)
            jobs_out.append(jd)

        if rows:
            db.table("jobs").upsert(rows, on_conflict="user_id,source_url").execute()

        if resume:
            jobs_out.sort(key=lambda j: j.fit_score or 0, reverse=True)

        return {
            "jobs_found": len(scraped),
            "jobs_queued": len(jobs_out),
            "scored": bool(resume),
            "jobs": [j.model_dump(mode="json") for j in jobs_out],
            "errors": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ── Applied status ────────────────────────────────────────────


@router.get("/applied-status")
async def get_applied_status(user_id: str = Depends(get_current_user_id)):
    db = get_db()
    resp = db.table("applications").select("job_id,id,status").eq("user_id", user_id).execute()
    return {r["job_id"]: {"app_id": r["id"], "status": r["status"]} for r in resp.data}


@router.get("/apply-clicks")
async def get_apply_clicks(user_id: str = Depends(get_current_user_id)):
    db = get_db()
    resp = db.table("apply_clicks").select("job_id,title,company").eq("user_id", user_id).execute()
    return {"count": len(resp.data), "jobs": resp.data}


# ── Per-job actions ───────────────────────────────────────────


@router.post("/{job_id}/click-apply")
async def click_apply(job_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    job_resp = db.table("jobs").select("data").eq("id", job_id).eq("user_id", user_id).maybe_single().execute()
    if job_resp.data:
        jd_data = job_resp.data["data"]
        db.table("apply_clicks").upsert({
            "user_id": user_id,
            "job_id": job_id,
            "title": jd_data.get("title"),
            "company": jd_data.get("company"),
        }, on_conflict="user_id,job_id").execute()
    count_resp = db.table("apply_clicks").select("job_id", count="exact").eq("user_id", user_id).execute()
    return {"tracked": True, "total_clicked": count_resp.count or 0}


@router.post("/{job_id}/mark-applied")
async def mark_applied(job_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_db()

    # Check already applied
    existing = db.table("applications").select("id,status").eq("job_id", job_id).eq("user_id", user_id).maybe_single().execute()
    if existing.data:
        return {
            "status": "already_applied",
            "app_id": existing.data["id"],
            "job_id": job_id,
            "current_status": existing.data["status"],
        }

    # Get the job
    job_resp = db.table("jobs").select("data").eq("id", job_id).eq("user_id", user_id).maybe_single().execute()
    if not job_resp.data:
        raise HTTPException(404, "Job not found in queue")

    jd_data = job_resp.data["data"]

    from datetime import datetime, UTC
    import uuid
    app_id = str(uuid.uuid4())

    db.table("applications").insert({
        "id": app_id,
        "user_id": user_id,
        "job_id": job_id,
        "job_snapshot": jd_data,
        "status": "submitted",
        "fit_score": jd_data.get("fit_score", 0.0),
        "submitted_at": datetime.now(UTC).isoformat(),
    }).execute()

    # Also record click
    db.table("apply_clicks").upsert({
        "user_id": user_id,
        "job_id": job_id,
        "title": jd_data.get("title"),
        "company": jd_data.get("company"),
    }, on_conflict="user_id,job_id").execute()

    return {"status": "applied", "app_id": app_id, "job_id": job_id, "current_status": "submitted"}


@router.patch("/{job_id}/application-status")
async def update_job_application_status(
    job_id: str,
    body: StatusUpdate,
    user_id: str = Depends(get_current_user_id),
):
    valid = {"submitted", "phone_screen", "interviewing", "offer", "rejected"}
    if body.status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {sorted(valid)}")

    db = get_db()
    resp = db.table("applications").select("id").eq("job_id", job_id).eq("user_id", user_id).maybe_single().execute()
    if not resp.data:
        raise HTTPException(404, "No application found for this job")

    app_id = resp.data["id"]
    db.table("applications").update({"status": body.status}).eq("id", app_id).execute()
    return {"job_id": job_id, "app_id": app_id, "new_status": body.status}


@router.post("/{job_id}/dismiss")
async def dismiss_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    resp = db.table("jobs").select("id").eq("id", job_id).eq("user_id", user_id).maybe_single().execute()
    if not resp.data:
        raise HTTPException(404, "Job not found")
    db.table("jobs").delete().eq("id", job_id).eq("user_id", user_id).execute()
    return {"status": "dismissed"}


@router.post("/{job_id}/select")
async def select_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    return {"status": "selected", "job_id": job_id}
