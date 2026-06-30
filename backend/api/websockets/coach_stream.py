"""WebSocket + SSE endpoints for real-time interview coaching answer streaming."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.auth_deps import get_current_user_id

ws_router = APIRouter()
sse_router = APIRouter()

_GRADE_SYSTEM = (
    "You are an expert interview coach. Grade the candidate's answer concisely "
    "and helpfully. Consider STAR structure, specificity, relevance, and delivery. "
    "Stream your feedback naturally as you evaluate."
)


def _build_grade_prompt(question_text: str, category: str, answer: str) -> str:
    return (
        f"Interview question ({category}): {question_text}\n\n"
        f"Candidate's answer: {answer}\n\n"
        "Provide streaming feedback covering: key strengths, main improvement areas, "
        "and an overall score estimate out of 10."
    )


# ── SSE endpoint ──────────────────────────────────────────────────────────────

class StreamQuestionRequest(BaseModel):
    session_id: str
    answer_text: str


@sse_router.post("/stream-question")
async def stream_question(
    request: StreamQuestionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Stream answer grading token-by-token via Server-Sent Events."""
    from backend.agents.coach.session_tracker import get_session

    session = get_session(request.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    question = session.current_question
    if not question:
        raise HTTPException(400, "No active question in this session")

    async def _event_stream():
        try:
            from backend.dependencies import anthropic_client
            client = anthropic_client.client

            async with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                system=_GRADE_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": _build_grade_prompt(
                        question.text, question.category, request.answer_text
                    ),
                }],
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except NotImplementedError:
            yield f"data: {json.dumps({'error': 'AI not configured'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@ws_router.websocket("/ws/coach/{session_id}")
async def coach_websocket(websocket: WebSocket, session_id: str):
    """WebSocket for real-time streaming answer grading. Accepts JSON messages with action='submit_answer'."""
    from backend.agents.coach.session_tracker import get_session

    await websocket.accept()

    session = get_session(session_id)
    if not session:
        await websocket.close(code=4004)
        return

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            action = payload.get("action")

            if action == "submit_answer":
                answer_text = payload.get("answer_text", "")
                question = session.current_question
                if not question:
                    await websocket.send_text(json.dumps({"error": "No active question"}))
                    continue

                try:
                    from backend.dependencies import anthropic_client
                    client = anthropic_client.client

                    async with client.messages.stream(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=500,
                        system=_GRADE_SYSTEM,
                        messages=[{
                            "role": "user",
                            "content": _build_grade_prompt(
                                question.text, question.category, answer_text
                            ),
                        }],
                    ) as stream:
                        async for text in stream.text_stream:
                            await websocket.send_text(json.dumps({"text": text}))

                    await websocket.send_text(json.dumps({"done": True}))

                except NotImplementedError:
                    await websocket.send_text(json.dumps({"error": "AI not configured"}))
                except Exception as exc:
                    await websocket.send_text(json.dumps({"error": str(exc)}))

            elif action == "ping":
                await websocket.send_text(json.dumps({"pong": True}))

    except WebSocketDisconnect:
        pass
