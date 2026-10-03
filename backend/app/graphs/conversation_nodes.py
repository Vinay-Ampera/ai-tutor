import re

from app.graphs.tutor_state import TutorState

IDENTITY_RESPONSE = (
    "I am your independent AI Tutor. I am here to help you learn and understand "
    "academic topics."
)
WELCOME_RESPONSE = (
    "Welcome! I am your AI Tutor. What academic topic would you like to learn "
    "about today?"
)
CAPABILITIES_RESPONSE = (
    "You can ask me to explain concepts, answer learning questions, create "
    "examples, or make study material across a wide range of academic and "
    "technical subjects, including mathematics, science, history, languages, "
    "economics, programming, and computer science. Ask about any topic you want "
    "to understand—for example, “What is a programming language?” or “Why do "
    "fractions need a common denominator?” I focus on learning, not unrelated "
    "tasks such as recipes, creative writing, or commercial work."
)
BASIC_CONVERSATION_RESPONSES = {
    "greeting": "Hello! I’m your AI Tutor. What would you like to learn about today?",
    "wellbeing": (
        "I’m doing well, thanks for asking! I’m ready to help you learn. "
        "What would you like to explore?"
    ),
    "thanks": "You’re welcome! Feel free to ask whenever you’re ready to learn more.",
    "farewell": "Goodbye! I’ll be here whenever you’re ready to learn something new.",
    "help": (
        "Of course! Tell me the topic or paste the part you’re unsure about, "
        "and I’ll explain it step by step."
    ),
}
OUT_OF_SCOPE_RESPONSE = (
    "I am here to help with learning and academic topics. I cannot help with "
    "that request, but you can ask me to explain a subject or concept."
)


def check_identity_intent(state: TutorState) -> dict[str, bool]:
    question = re.sub(r"\s+", " ", state["user_question"].strip().lower())
    is_identity_query = bool(
        re.search(r"\b(?:who|what)\s+(?:exactly\s+)?are\s+you\b", question)
        or re.search(
            r"\b(?:what is|what's|whats)\s+your\s+(?:name|identity)\b",
            question,
        )
        or re.search(r"\btell me about yourself\b", question)
        or re.search(
            r"\b(?:are|aren't)\s+you\s+(?:an?\s+)?"
            r"(?:ai|bot|human|gemini|google|chatbot|language model|llm)\b",
            question,
        )
        or re.search(
            r"\b(?:are|aren't)\s+you\b.*\b(?:gemini|google|llm)\b",
            question,
        )
        or re.search(r"\bwho\s+(?:made|created|built)\s+you\b", question)
        or re.search(
            r"\b(?:what|which)\s+(?:(?:ai|language|llm)\s+)?model\s+are\s+you\b",
            question,
        )
        or re.search(r"\bidentify\s+yourself\b", question)
    )
    return {"is_identity_query": is_identity_query}


def route_after_identity(state: TutorState) -> str:
    return "identity" if state["is_identity_query"] else "check_capabilities"


def check_capabilities_intent(state: TutorState) -> dict[str, bool]:
    question = re.sub(r"\s+", " ", state["user_question"].strip().lower())
    is_capabilities_query = bool(
        re.fullmatch(
            r"(?:hi[, ]+)?(?:"
            r"what (?:can i ask|i can ask) you(?: and what can you do)?|"
            r"what can you do|"
            r"what can you help(?: me)? with|"
            r"what (?:subjects|topics) can you (?:teach|help with)|"
            r"what do you help with|"
            r"what are you able to help with|"
            r"what are your capabilities"
            r")[?.! ]*",
            question,
        )
    )
    return {"is_capabilities_query": is_capabilities_query}


def check_basic_conversation_intent(state: TutorState) -> dict[str, str | None]:
    question = re.sub(r"\s+", " ", state["user_question"].strip().lower())
    question = re.sub(r"[?.!,]+$", "", question).strip()
    patterns = {
        "greeting": (
            r"(?:hi|hello|hey|howdy|greetings)(?: there)?",
            r"good (?:morning|afternoon|evening)",
        ),
        "wellbeing": (
            r"(?:hi|hello|hey)[, ]+how are you(?: doing)?(?: today)?",
            r"good (?:morning|afternoon|evening)[, ]+how are you(?: doing)?",
            r"how are you(?: doing)?(?: today)?",
            r"how(?:'s| is) it going(?: today)?",
        ),
        "thanks": (
            r"(?:hi|hello|hey)[, ]+(?:thanks|thank you)(?: so much| a lot)?",
            r"(?:thanks|thank you)(?: so much| a lot)?",
            r"i appreciate it",
        ),
        "farewell": (
            r"(?:bye|goodbye|see you|talk to you later)(?: soon)?",
        ),
        "help": (
            r"(?:hi|hello|hey)[, ]+(?:can|could|would) you help me(?: please)?",
            r"(?:can|could|would) you help me(?: please)?",
            r"(?:hi|hello|hey)[, ]+(?:can|could) you explain (?:that|this|it)(?: again)?",
            r"(?:can|could) you explain (?:that|this|it)(?: again)?",
            r"please explain (?:that|this|it)(?: again)?",
            r"i (?:do not|don't) understand",
            r"help me understand",
            r"help",
        ),
    }
    for kind, candidates in patterns.items():
        if any(re.fullmatch(candidate, question) for candidate in candidates):
            return {"basic_conversation_kind": kind}
    return {"basic_conversation_kind": None}


def route_after_basic_conversation(state: TutorState) -> str:
    return "basic_conversation" if state["basic_conversation_kind"] else "classify"


def respond_to_identity(_: TutorState) -> dict[str, str | bool]:
    return {
        "response": IDENTITY_RESPONSE,
        "request_category": None,
        "is_greeting": False,
        "is_educational": False,
        "next_action": "identity_response",
    }


def respond_to_capabilities(_: TutorState) -> dict[str, str]:
    return {"response": CAPABILITIES_RESPONSE, "next_action": "capabilities_response"}


def respond_to_basic_conversation(state: TutorState) -> dict[str, str | bool]:
    kind = state["basic_conversation_kind"]
    if kind not in BASIC_CONVERSATION_RESPONSES:
        raise ValueError(f"Unsupported basic conversation kind: {kind}")
    is_greeting = kind in ("greeting", "wellbeing", "thanks", "farewell")
    return {
        "response": BASIC_CONVERSATION_RESPONSES[kind],
        "request_category": "greeting" if is_greeting else "educational",
        "is_greeting": is_greeting,
        "is_educational": not is_greeting,
        "next_action": kind,
    }


def respond_to_greeting(_: TutorState) -> dict[str, str]:
    return {"response": WELCOME_RESPONSE, "next_action": "welcome"}


def respond_out_of_scope(_: TutorState) -> dict[str, str]:
    return {"response": OUT_OF_SCOPE_RESPONSE, "next_action": "refusal"}
