import json
import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool, model_validator

from app.graphs.generation_support import parse_json_response
from app.graphs.conversation_nodes import OUT_OF_SCOPE_RESPONSE
from app.graphs.tutor_prompts import SCOPE_CLASSIFICATION_PROMPT
from app.graphs.tutor_state import TutorState
from app.services import gemini
from app.services.gemini import GeminiRequestError

logger = logging.getLogger(__name__)


class ScopeClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request_category: Literal["greeting", "educational", "out_of_scope"]
    is_greeting: StrictBool
    is_educational: StrictBool

    @model_validator(mode="after")
    def flags_match_category(self) -> "ScopeClassification":
        expected = {
            "greeting": (True, False),
            "educational": (False, True),
            "out_of_scope": (False, False),
        }[self.request_category]
        if (self.is_greeting, self.is_educational) != expected:
            raise ValueError("Classification flags do not match the category.")
        return self


def classify_scope(state: TutorState) -> dict[str, str | bool]:
    try:
        raw = gemini.generate_text(
            SCOPE_CLASSIFICATION_PROMPT.format(
                request_data=json.dumps(
                    {
                        "requested_action": state["requested_action"],
                        "active_quiz_question": state["quiz_question"],
                        "learner_message": state["user_question"],
                    },
                    ensure_ascii=False,
                )
            )
        )
        classification = ScopeClassification.model_validate(
            parse_json_response(raw)
        )
    except GeminiRequestError:
        raise
    except Exception as error:
        logger.warning(
            "Scope classification output was invalid (%s); refusing the request.",
            type(error).__name__,
        )
        return {
            "request_category": "out_of_scope",
            "is_greeting": False,
            "is_educational": False,
            "response": OUT_OF_SCOPE_RESPONSE,
            "next_action": "refusal",
        }

    return {
        "request_category": classification.request_category,
        "is_greeting": classification.is_greeting,
        "is_educational": classification.is_educational,
        "next_action": classification.request_category,
    }


def route_after_classification(state: TutorState) -> str:
    category = state["request_category"]
    if category != "educational":
        return category or "out_of_scope"
    return {
        "teach": "teaching_approach",
        "explain_more": "explain_more",
        "another_example": "another_example",
        "quiz": "quiz",
        "evaluate_quiz": "quiz_evaluation",
    }.get(state["requested_action"], "out_of_scope")
