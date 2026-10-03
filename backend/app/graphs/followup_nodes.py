from app.graphs.generation_support import (
    build_prompt,
    generate_content,
    require_context,
)
from app.graphs.tutor_prompts import ANOTHER_EXAMPLE, EXPLAIN_MORE
from app.graphs.tutor_state import TutorState


def explain_more(state: TutorState) -> dict[str, str]:
    prompt = build_prompt(
        EXPLAIN_MORE,
        learner_question=require_context(state, "user_question"),
        topic=require_context(state, "topic"),
        student_level=require_context(state, "student_level"),
        previous_explanation=require_context(state, "explanation"),
    )
    explanation = generate_content(prompt)
    return {
        "explanation": explanation,
        "response": explanation,
        "next_action": "explain_more",
    }


def generate_another_example(state: TutorState) -> dict[str, str]:
    prompt = build_prompt(
        ANOTHER_EXAMPLE,
        topic=require_context(state, "topic"),
        student_level=require_context(state, "student_level"),
        previous_example=require_context(state, "example"),
        explanation=require_context(state, "explanation"),
    )
    example = generate_content(prompt)
    return {
        "example": example,
        "response": example,
        "next_action": "another_example",
    }
