"""Call lifecycle endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_session
from schemas import (
    EndCallIn,
    EndCallOut,
    GetResponsesOut,
    QuestionResponseOut,
    SendMessageIn,
    SendMessageOut,
    StartCallIn,
    StartCallOut,
    TranscriptMessageOut,
)
from services import call_service

router = APIRouter(prefix="/api/call", tags=["calls"])


@router.post("/start", response_model=StartCallOut)
async def start_call(req: StartCallIn, session: AsyncSession = Depends(get_session)):
    call_id = req.call_id or f"call_{uuid.uuid4().hex[:12]}"
    try:
        call, greeting = await call_service.start_call(
            session,
            call_id=call_id,
            patient_id=req.patient_id,
            tone=req.config.tone,
            speed=req.config.speed,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StartCallOut(
        call_id=call.id,
        status="in-progress",
        greeting_message=greeting,
    )


@router.post("/{call_id}/message", response_model=SendMessageOut)
async def send_message(
    call_id: str, req: SendMessageIn, session: AsyncSession = Depends(get_session)
):
    try:
        agent_message, captured, q_index, ui_status = await call_service.process_message(
            session,
            call_id=call_id,
            user_message=req.message,
            timestamp=req.timestamp,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    captured_out = None
    if captured is not None:
        captured_out = QuestionResponseOut(**captured)

    return SendMessageOut(
        agent_message=agent_message,
        captured_response=captured_out,
        current_question_index=q_index,
        call_status=ui_status,
    )


@router.get("/{call_id}/responses", response_model=GetResponsesOut)
async def get_responses(call_id: str, session: AsyncSession = Depends(get_session)):
    call, responses, transcript, duration = await call_service.get_call_state(session, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    return GetResponsesOut(
        call_id=call_id,
        responses=[
            QuestionResponseOut(
                question_index=r.question_index,
                question=r.question_text,
                answer=r.normalized_answer or r.raw_answer or None,
                status=r.status,
            )
            for r in responses
        ],
        completeness=call.completeness,
        transcript=[
            TranscriptMessageOut(
                id=str(t.id),
                role=t.role,
                text=t.message,
                timestamp=t.timestamp,
            )
            for t in transcript
        ],
        outcome=call.outcome,
        duration_seconds=duration,
    )


@router.post("/{call_id}/end", response_model=EndCallOut)
async def end_call(
    call_id: str, req: EndCallIn, session: AsyncSession = Depends(get_session)
):
    try:
        call = await call_service.end_call(session, call_id=call_id, reason=req.reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if call is None:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    responses = await call_service.get_call_state(session, call_id)
    _, resp_list, transcript_list, duration = responses

    return EndCallOut(
        call_id=call_id,
        outcome=call.outcome or "incomplete",
        duration_seconds=call.duration_secs or 0.0,
        responses=[
            QuestionResponseOut(
                question_index=r.question_index,
                question=r.question_text,
                answer=r.normalized_answer or r.raw_answer or None,
                status=r.status,
            )
            for r in resp_list
        ],
        completeness=call.completeness,
        transcript=[
            TranscriptMessageOut(
                id=str(t.id),
                role=t.role,
                text=t.message,
                timestamp=t.timestamp,
            )
            for t in transcript_list
        ],
    )
