import json
import re
from typing import Any

from app.graphs.tutor_prompts import build_generation_prompt
from app.graphs.tutor_state import TutorState
from app.services import gemini
from app.services.gemini import GeminiRequestError


def parse_json_response(raw_response: str) -> object:
    cleaned = raw_response.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
    return json.loads(cleaned)


def generate_content(prompt: str) -> str:
    content = gemini.generate_text(prompt).strip()
    if not content:
        raise GeminiRequestError("Tutor generation returned an empty response.")

    identity_terms = (
        r"(?:google|gemini|(?:large\s+)?language model|llm|chatbot|ai assistant)"
    )
    self_identification = re.search(
        rf"\b(?:i am|i'm)\s+(?:(?:an?|the)\s+)?{identity_terms}\b"
        rf"|\bas\s+(?:(?:an?|the)\s+)?{identity_terms}\b[^.!?]{{0,40}}\bi\b",
        content,
        re.IGNORECASE,
    )
    if self_identification:
        raise GeminiRequestError(
            "Tutor generation did not meet the AI Tutor identity requirements."
        )
    return content


def require_context(state: TutorState, key: str) -> str:
    value = state.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GeminiRequestError(f"Missing lesson context: {key}.")
    return value.strip()


def build_prompt(task_instructions: str, **learner_data: Any) -> str:
    return build_generation_prompt(task_instructions, **learner_data)


__all__ = ["build_prompt", "generate_content", "parse_json_response", "require_context"]
