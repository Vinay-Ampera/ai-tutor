from pydantic import BaseModel, ConfigDict, field_validator

from app.graphs.generation_support import (
    build_prompt,
    generate_content,
    parse_json_response,
    require_context,
)
from app.graphs.tutor_prompts import EVALUATE_QUIZ, GENERATE_QUIZ
from app.graphs.tutor_state import TutorState
from app.services.gemini import GeminiRequestError


class QuizItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str
    expected_answer: str

    @field_validator("question", "expected_answer")
    @classmethod
    def require_nonblank_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Quiz values must not be blank.")
        return cleaned


def generate_quiz(state: TutorState) -> dict[str, str]:
    prompt = build_prompt(
        GENERATE_QUIZ,
        topic=require_context(state, "topic"),
        student_level=require_context(state, "student_level"),
        explanation=require_context(state, "explanation"),
        example=require_context(state, "example"),
    )
    try:
        quiz_item = QuizItem.model_validate(
            parse_json_response(generate_content(prompt))
        )
    except GeminiRequestError:
        raise
    except Exception as error:
        raise GeminiRequestError(
            "Tutor could not create a valid quiz question."
        ) from error
    return {
        "quiz_question": quiz_item.question,
        "expected_quiz_answer": quiz_item.expected_answer,
        "response": quiz_item.question,
        "next_action": "quiz",
    }


def evaluate_quiz_answer(state: TutorState) -> dict[str, str]:
    prompt = build_prompt(
        EVALUATE_QUIZ,
        topic=require_context(state, "topic"),
        student_level=require_context(state, "student_level"),
        quiz_question=require_context(state, "quiz_question"),
        expected_answer=require_context(state, "expected_quiz_answer"),
        user_answer=require_context(state, "user_answer"),
    )
    evaluation = generate_content(prompt)
    return {
        "evaluation": evaluation,
        "response": evaluation,
        "next_action": "quiz_evaluation",
    }
