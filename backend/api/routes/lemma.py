"""Lemma pod integration — approval queue read/write and pod stats."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


def _pod():
    from backend.lemma_client import get_pod
    return get_pod()


class ApprovalIn(BaseModel):
    agent_id: str
    agent_name: str
    summary: str


@router.post("/approvals")
async def create_approval(body: ApprovalIn):
    """Write a new pending approval to the Lemma pod."""
    try:
        pod = _pod()
        row = pod.table("approvals").create({
            "agent_id": body.agent_id,
            "agent_name": body.agent_name,
            "summary": body.summary,
            "status": "pending",
        })
        return {"created": True, "row": row}
    except Exception:
        return {"created": False}


@router.get("/approvals")
async def list_approvals():
    """List pending approvals from the Lemma pod."""
    try:
        pod = _pod()
        result = pod.records.list("approvals")
        items = result.to_dict().get("items", [])
        pending = [i for i in items if i.get("status", "pending") == "pending"]
        return {"approvals": pending, "count": len(pending)}
    except Exception:
        return {"approvals": [], "count": 0}


@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str):
    """Mark an approval as approved in the Lemma pod."""
    try:
        pod = _pod()
        pod.table("approvals").update(approval_id, {"status": "approved"})
        return {"status": "approved", "id": approval_id}
    except Exception:
        return {"status": "approved", "id": approval_id, "synced": False}


@router.post("/approvals/{approval_id}/skip")
async def skip_action(approval_id: str):
    """Mark an approval as skipped in the Lemma pod."""
    try:
        pod = _pod()
        pod.table("approvals").update(approval_id, {"status": "skipped"})
        return {"status": "skipped", "id": approval_id}
    except Exception:
        return {"status": "skipped", "id": approval_id, "synced": False}


@router.get("/stats")
async def pod_stats():
    """Row counts from the Lemma pod for the connection card."""
    try:
        pod = _pod()
        approvals_items = pod.records.list("approvals").to_dict().get("items", [])
        approvals_count = len(approvals_items)
        try:
            activity_items = pod.records.list("agent_activity").to_dict().get("items", [])
            activity_count = len(activity_items)
        except Exception:
            activity_count = 0
        return {
            "connected": True,
            "approvals_count": approvals_count,
            "activity_count": activity_count,
            "total_rows": approvals_count + activity_count,
        }
    except Exception:
        return {"connected": False, "approvals_count": 0, "activity_count": 0, "total_rows": 0}
