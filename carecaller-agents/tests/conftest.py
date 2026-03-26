"""Shared test fixtures for carecaller-agents."""

import pytest

from carecaller_agents.models.patient import PatientContext
from carecaller_agents.models.responses import Question


@pytest.fixture
def sample_patient() -> PatientContext:
    return PatientContext(
        id="pat_001",
        name="Gabriella Shelton",
        date_of_birth="1985-07-22",
        medication="Tirzepatide",
        dosage="2.5mg weekly injection",
        pharmacy="CVS Pharmacy",
        phone="+1-555-0101",
    )


@pytest.fixture
def health_questions() -> list[Question]:
    return Question.all_questions()
