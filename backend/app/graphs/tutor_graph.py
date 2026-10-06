from threading import Lock
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.graphs.assessment_nodes import evaluate_quiz_answer, generate_quiz
from app.graphs.classification_nodes import classify_scope, route_after_classification
from app.graphs.conversation_nodes import (
    check_capabilities_intent,
    check_basic_conversation_intent,
    check_identity_intent,
    respond_out_of_scope,
    respond_to_capabilities,
    respond_to_basic_conversation,
    respond_to_greeting,
    respond_to_identity,
    route_after_basic_conversation,
    route_after_identity,
)
from app.graphs.followup_nodes import explain_more, generate_another_example
from app.graphs.retrieval_nodes import (
    check_document_readiness,
    generate_document_answer,
    retrieve_document_context,
)
from app.graphs.teaching_nodes import (
    generate_example,
    generate_explanation,
    select_teaching_approach,
)
from app.graphs.tutor_state import TutorAction, TutorState


def build_tutor_graph():
    graph = StateGraph(TutorState)
    graph.add_node("check_identity", check_identity_intent)
    graph.add_node("identity_response", respond_to_identity)
    graph.add_node("check_capabilities", check_capabilities_intent)
    graph.add_node("capabilities_response", respond_to_capabilities)
    graph.add_node("check_basic_conversation", check_basic_conversation_intent)
    graph.add_node("basic_conversation_response", respond_to_basic_conversation)
    graph.add_node("classify_scope", classify_scope)
    graph.add_node("greeting_response", respond_to_greeting)
    graph.add_node("out_of_scope_response", respond_out_of_scope)
    graph.add_node("teaching_approach", select_teaching_approach)
    graph.add_node("explanation", generate_explanation)
    graph.add_node("example", generate_example)
    graph.add_node("explain_more", explain_more)
    graph.add_node("another_example", generate_another_example)
    graph.add_node("quiz", generate_quiz)
    graph.add_node("quiz_evaluation", evaluate_quiz_answer)
    graph.add_node("document_readiness", check_document_readiness)
    graph.add_node("document_retrieval", retrieve_document_context)
    graph.add_node("document_answer", generate_document_answer)

    graph.add_edge(START, "check_identity")
    graph.add_conditional_edges(
        "check_identity",
        route_after_identity,
        {
            "identity": "identity_response",
            "check_capabilities": "check_capabilities",
        },
    )
    graph.add_edge("identity_response", END)
    graph.add_conditional_edges(
        "check_capabilities",
        lambda state: (
            "capabilities"
            if state["is_capabilities_query"]
            else "check_basic_conversation"
        ),
        {
            "capabilities": "capabilities_response",
            "check_basic_conversation": "check_basic_conversation",
        },
    )
    graph.add_edge("capabilities_response", END)
    graph.add_conditional_edges(
        "check_basic_conversation",
        route_after_basic_conversation,
        {
            "basic_conversation": "basic_conversation_response",
            "classify": "classify_scope",
        },
    )
    graph.add_edge("basic_conversation_response", END)
    graph.add_conditional_edges(
        "classify_scope",
        route_after_classification,
        {
            "greeting": "greeting_response",
            "teaching_approach": "teaching_approach",
            "explain_more": "explain_more",
            "another_example": "another_example",
            "quiz": "quiz",
            "quiz_evaluation": "quiz_evaluation",
            "document_readiness": "document_readiness",
            "out_of_scope": "out_of_scope_response",
        },
    )
    graph.add_conditional_edges(
        "document_readiness",
        lambda state: state["next_action"],
        {
            "document_not_ready": END,
            "document_retrieval": "document_retrieval",
        },
    )
    graph.add_conditional_edges(
        "document_retrieval",
        lambda state: state["next_action"],
        {
            "document_answer": "document_answer",
            "document_not_found": END,
        },
    )
    graph.add_edge("teaching_approach", "explanation")
    graph.add_edge("explanation", "example")
    graph.add_edge("greeting_response", END)
    graph.add_edge("out_of_scope_response", END)
    graph.add_edge("example", END)
    graph.add_edge("explain_more", END)
    graph.add_edge("another_example", END)
    graph.add_edge("quiz", END)
    graph.add_edge("quiz_evaluation", END)
    graph.add_edge("document_answer", END)
    return graph.compile()


tutor_graph = build_tutor_graph()

_session_entries_lock = Lock()


class _SessionEntry:
    def __init__(self) -> None:
        self.lock = Lock()
        self.state: TutorState | None = None


_session_entries: dict[str, _SessionEntry] = {}


def run_tutor_graph(
    user_question: str,
    session_id: str | None = None,
    requested_action: TutorAction = "teach",
    lesson_context: dict[str, str | None] | None = None,
) -> TutorState:
    active_session_id = session_id or uuid4().hex
    context = lesson_context or {}
    initial_state: TutorState = {
        "session_id": active_session_id,
        "user_question": user_question,
        "request_category": None,
        "is_identity_query": False,
        "is_capabilities_query": False,
        "basic_conversation_kind": None,
        "is_greeting": False,
        "is_educational": False,
        "requested_action": requested_action,
        "quiz_question": context.get("quiz_question"),
        "expected_quiz_answer": context.get("expected_quiz_answer"),
        "user_answer": context.get("user_answer"),
        "evaluation": None,
        "topic": context.get("topic"),
        "student_level": context.get("student_level"),
        "teaching_approach": context.get("teaching_approach"),
        "explanation": context.get("explanation"),
        "example": context.get("example"),
        "is_document_question": False,
        "document_id": None,
        "document_name": None,
        "retrieved_chunks": [],
        "next_action": "scope_check",
        "response": "",
    }
    while True:
        with _session_entries_lock:
            entry = _session_entries.setdefault(
                active_session_id,
                _SessionEntry(),
            )

        with entry.lock:
            with _session_entries_lock:
                if _session_entries.get(active_session_id) is not entry:
                    continue

                previous_state = entry.state
                if previous_state is not None:
                    if initial_state["topic"] is None:
                        initial_state["topic"] = previous_state["topic"]
                    if initial_state["student_level"] is None:
                        initial_state["student_level"] = previous_state["student_level"]
                    if initial_state["teaching_approach"] is None:
                        initial_state["teaching_approach"] = previous_state[
                            "teaching_approach"
                        ]
                    if initial_state["explanation"] is None:
                        initial_state["explanation"] = previous_state["explanation"]
                    if initial_state["example"] is None:
                        initial_state["example"] = previous_state["example"]
                    if initial_state["quiz_question"] is None:
                        initial_state["quiz_question"] = previous_state["quiz_question"]
                    if initial_state["expected_quiz_answer"] is None:
                        initial_state["expected_quiz_answer"] = previous_state[
                            "expected_quiz_answer"
                        ]

            result = tutor_graph.invoke(initial_state)
            entry.state = result
            return result


def clear_tutor_session(session_id: str) -> None:
    with _session_entries_lock:
        entry = _session_entries.get(session_id)
    if entry is None:
        return

    with entry.lock:
        with _session_entries_lock:
            if _session_entries.get(session_id) is entry:
                del _session_entries[session_id]


def has_tutor_session_context(
    session_id: str,
    requested_action: TutorAction,
) -> bool:
    with _session_entries_lock:
        entry = _session_entries.get(session_id)
    if entry is None:
        return False

    with entry.lock:
        with _session_entries_lock:
            if _session_entries.get(session_id) is not entry:
                return False
            state = entry.state

        if state is None:
            return False

        required_context = ("topic", "student_level", "explanation")
        if requested_action == "another_example":
            required_context += ("example",)
        return all(state.get(key) for key in required_context)
