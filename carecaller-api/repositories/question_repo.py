"""Read-only access to the 14 health check-in questions.

Questions are static — defined in carecaller_agents.models.responses.
No database table needed.
"""

from __future__ import annotations

from carecaller_agents.models.responses import Question


def get_all_questions() -> list[Question]:
    """Return the 14 TrimRX health check-in questions."""
    return Question.all_questions()
