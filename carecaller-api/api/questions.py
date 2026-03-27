"""Questions endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from repositories import question_repo
from schemas import QuestionOut, QuestionsListOut

router = APIRouter(prefix="/api", tags=["questions"])


@router.get("/questions", response_model=QuestionsListOut)
async def list_questions():
    questions = question_repo.get_all_questions()
    return QuestionsListOut(
        questions=[QuestionOut(index=q.index, text=q.text) for q in questions]
    )
