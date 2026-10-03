from pydantic import BaseModel, ConfigDict, field_validator

from app.graphs.generation_support import (
    build_prompt,
    generate_content,
    parse_json_response,
    require_context,
)
from app.graphs.tutor_prompts import (
    GENERATE_EXAMPLE,
    GENERATE_EXPLANATION,
    SELECT_TEACHING_APPROACH,
)
from app.graphs.tutor_state import TutorState
from app.services.gemini import GeminiRequestError


class TeachingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    topic: str
    student_level: str
    teaching_approach: str

    @field_validator("topic", "student_level", "teaching_approach")
    @classmethod
    def require_nonblank_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Teaching plan values must not be blank.")
        return cleaned


def select_teaching_approach(state: TutorState) -> dict[str, str]:
    prompt = build_prompt(
        SELECT_TEACHING_APPROACH,
        learner_question=require_context(state, "user_question"),
    )
    try:
        plan = TeachingPlan.model_validate(
            parse_json_response(generate_content(prompt))
        )
    except GeminiRequestError:
        raise
    except Exception as error:
        raise GeminiRequestError(
            "Tutor could not create a valid teaching plan."
        ) from error
    return {
        "topic": plan.topic,
        "student_level": plan.student_level,
        "teaching_approach": plan.teaching_approach,
        "next_action": "explanation",
    }


def generate_explanation(state: TutorState) -> dict[str, str]:
    prompt = build_prompt(
        GENERATE_EXPLANATION,
        learner_question=require_context(state, "user_question"),
        topic=require_context(state, "topic"),
        student_level=require_context(state, "student_level"),
        teaching_approach=require_context(state, "teaching_approach"),
    )
    return {
        "explanation": generate_content(prompt),
        "next_action": "example",
    }


def generate_example(state: TutorState) -> dict[str, str]:
    prompt = build_prompt(
        GENERATE_EXAMPLE,
        topic=require_context(state, "topic"),
        student_level=require_context(state, "student_level"),
        explanation=require_context(state, "explanation"),
    )
    example = generate_content(prompt)
    explanation = require_context(state, "explanation")
    return {
        "example": example,
        "response": f"## Explanation\n\n{explanation}\n\n## Example\n\n{example}",
        "next_action": "teaching",
    }
