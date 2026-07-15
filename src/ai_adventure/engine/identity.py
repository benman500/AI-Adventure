"""Personality questions: validate and store answers only."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from ai_adventure.engine.errors import EngineValidationError

_QUESTIONS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "identity" / "personality_questions.json"
)


class PersonalityAnswerOption(BaseModel):
    """One selectable answer for a personality question."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class PersonalityQuestion(BaseModel):
    """One universal personality question."""

    id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    answers: list[PersonalityAnswerOption] = Field(min_length=2)

    @field_validator("answers")
    @classmethod
    def _unique_answer_ids(
        cls,
        value: list[PersonalityAnswerOption],
    ) -> list[PersonalityAnswerOption]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("answer ids must be unique within a question")
        return value


class PersonalityQuestionSet(BaseModel):
    """Full set of creation personality questions."""

    questions: list[PersonalityQuestion] = Field(min_length=1)

    @field_validator("questions")
    @classmethod
    def _unique_question_ids(
        cls,
        value: list[PersonalityQuestion],
    ) -> list[PersonalityQuestion]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("question ids must be unique")
        return value


@lru_cache(maxsize=1)
def load_personality_questions(path: str | None = None) -> PersonalityQuestionSet:
    """Load personality questions from content data."""

    questions_path = Path(path) if path else _QUESTIONS_PATH
    try:
        raw = json.loads(questions_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EngineValidationError("Personality questions data file missing") from exc
    except json.JSONDecodeError as exc:
        raise EngineValidationError("Corrupted personality questions data") from exc
    try:
        return PersonalityQuestionSet.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid personality questions data: {exc}") from exc


def clear_personality_questions_cache() -> None:
    """Clear cached questions (tests / alternate content)."""

    load_personality_questions.cache_clear()


def list_personality_questions(
    path: str | None = None,
) -> list[PersonalityQuestion]:
    """Return the ordered list of personality questions."""

    return list(load_personality_questions(path).questions)


def validate_identity_answers(
    answers: dict[str, str],
    path: str | None = None,
) -> dict[str, str]:
    """Validate that answers cover every question with a legal option.

    Stores answers only—does not assign traits, Dao, or alignment.
    """

    question_set = load_personality_questions(path)
    expected = {question.id: {option.id for option in question.answers} for question in question_set.questions}

    if set(answers.keys()) != set(expected.keys()):
        missing = sorted(set(expected.keys()) - set(answers.keys()))
        extra = sorted(set(answers.keys()) - set(expected.keys()))
        parts: list[str] = []
        if missing:
            parts.append(f"missing answers for: {', '.join(missing)}")
        if extra:
            parts.append(f"unknown questions: {', '.join(extra)}")
        raise EngineValidationError("; ".join(parts))

    validated: dict[str, str] = {}
    for question_id, answer_id in answers.items():
        if answer_id not in expected[question_id]:
            raise EngineValidationError(
                f"Invalid answer {answer_id!r} for question {question_id!r}"
            )
        validated[question_id] = answer_id
    return validated
