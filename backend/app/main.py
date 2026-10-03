from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.graphs.tutor_graph import (
    clear_tutor_session,
    has_tutor_session_context,
    run_tutor_graph,
)
from app.graphs.tutor_state import TutorAction
from app.services.gemini import (
    GeminiConfigurationError,
    GeminiQuotaError,
    GeminiRequestError,
)

app = FastAPI(title="AI Tutor API")
SERVER_INSTANCE_ID = uuid4().hex
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["DELETE", "GET", "POST"],
    allow_headers=["Content-Type"],
)


class GeminiRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)
    action: TutorAction = "teach"
    topic: str | None = Field(default=None, max_length=300)
    student_level: str | None = Field(default=None, max_length=100)
    teaching_approach: str | None = Field(default=None, max_length=500)
    explanation: str | None = Field(default=None, max_length=6000)
    example: str | None = Field(default=None, max_length=4000)
    quiz_question: str | None = Field(default=None, max_length=2000)
    expected_quiz_answer: str | None = Field(default=None, max_length=2000)
    user_answer: str | None = Field(default=None, max_length=2000)


class TutorActionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)


class GeminiResponse(BaseModel):
    text: str
    session_id: str
    follow_up_available: bool


@app.get("/")
def root():
    return {
        "message": "AI Tutor API is running",
        "server_instance_id": SERVER_INSTANCE_ID,
    }


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> None:
    clear_tutor_session(session_id)


def _run_tutor_request(
    prompt: str,
    session_id: str | None,
    requested_action: TutorAction,
    lesson_context: dict[str, str | None] | None = None,
) -> GeminiResponse:
    try:
        result = run_tutor_graph(
            prompt,
            session_id,
            requested_action=requested_action,
            lesson_context=lesson_context,
        )
    except GeminiQuotaError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except GeminiConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except GeminiRequestError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    follow_up_available = all(
        result.get(key)
        for key in ("topic", "student_level", "explanation", "example")
    )
    return GeminiResponse(
        text=result["response"],
        session_id=result["session_id"],
        follow_up_available=follow_up_available,
    )


@app.post("/api/gemini/generate", response_model=GeminiResponse)
def generate_gemini_response(request: GeminiRequest) -> GeminiResponse:
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt must not be empty.")

    return _run_tutor_request(
        request.prompt,
        request.session_id,
        request.action,
        lesson_context={
            "topic": request.topic,
            "student_level": request.student_level,
            "teaching_approach": request.teaching_approach,
            "explanation": request.explanation,
            "example": request.example,
            "quiz_question": request.quiz_question,
            "expected_quiz_answer": request.expected_quiz_answer,
            "user_answer": request.user_answer,
        },
    )


@app.post("/api/tutor/explain-more", response_model=GeminiResponse)
def explain_more_endpoint(request: TutorActionRequest) -> GeminiResponse:
    if not has_tutor_session_context(request.session_id, "explain_more"):
        raise HTTPException(
            status_code=409,
            detail="Ask a learning question before requesting a deeper explanation.",
        )

    return _run_tutor_request(
        "Explain more about the current lesson.",
        request.session_id,
        "explain_more",
    )


@app.post("/api/tutor/example", response_model=GeminiResponse)
def another_example(request: TutorActionRequest) -> GeminiResponse:
    if not has_tutor_session_context(request.session_id, "another_example"):
        raise HTTPException(
            status_code=409,
            detail="Ask a learning question before requesting another example.",
        )

    return _run_tutor_request(
        "Give me another example for the current lesson.",
        request.session_id,
        "another_example",
    )