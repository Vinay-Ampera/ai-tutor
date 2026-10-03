from typing import Literal, TypedDict


RequestCategory = Literal["greeting", "educational", "out_of_scope"]
TutorAction = Literal[
    "teach",
    "explain_more",
    "another_example",
    "quiz",
    "evaluate_quiz",
]


class TutorState(TypedDict):
    session_id: str
    user_question: str
    request_category: RequestCategory | None
    is_identity_query: bool
    is_capabilities_query: bool
    basic_conversation_kind: (
        Literal["greeting", "wellbeing", "thanks", "farewell", "help"] | None
    )
    is_greeting: bool
    is_educational: bool
    topic: str | None
    student_level: str | None
    teaching_approach: str | None
    explanation: str | None
    example: str | None
    requested_action: TutorAction
    quiz_question: str | None
    expected_quiz_answer: str | None
    user_answer: str | None
    evaluation: str | None
    next_action: str
    response: str
