from uuid import uuid4

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.graphs.tutor_graph import run_tutor_graph
from app.graphs.tutor_state import TutorAction
from app.session_store import TutorMessage, session_store
from app.services.gemini import (
    GeminiConfigurationError,
    GeminiQuotaError,
    GeminiRequestError,
)

app = FastAPI(title="AI Tutor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "DELETE"],
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


class GeminiResponse(BaseModel):
    text: str
    session_id: str


class TutorMessageResponse(BaseModel):
    role: str
    content: str


class TutorSessionResponse(BaseModel):
    messages: list[TutorMessageResponse]


@app.get("/")
def root():
    return {"message": "AI Tutor API is running"}


@app.post("/api/gemini/generate", response_model=GeminiResponse)
def generate_gemini_response(request: GeminiRequest) -> GeminiResponse:
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt must not be empty.")

    session_id = request.session_id or uuid4().hex
    session = session_store.get_or_create(session_id)
    with session.lock:
        try:
            result = run_tutor_graph(
                request.prompt,
                session_id,
                requested_action=request.action,
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
                prior_state=session.state,
            )
        except GeminiQuotaError as error:
            raise HTTPException(status_code=429, detail=str(error)) from error
        except GeminiConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except GeminiRequestError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

        session.state = result
        session.messages.extend(
            [
                {"role": "user", "content": request.prompt.strip()},
                {"role": "assistant", "content": result["response"]},
            ]
        )

    return GeminiResponse(text=result["response"], session_id=session_id)


@app.get(
    "/api/sessions/{session_id}",
    response_model=TutorSessionResponse,
)
def get_tutor_session(
    session_id: str = Path(min_length=1, max_length=100),
) -> TutorSessionResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Tutor session was not found.")

    with session.lock:
        messages: list[TutorMessageResponse] = [
            TutorMessageResponse(**message) for message in session.messages
        ]
    return TutorSessionResponse(messages=messages)


@app.delete("/api/sessions/{session_id}", status_code=204)
def clear_tutor_session(
    session_id: str = Path(min_length=1, max_length=100),
) -> None:
    session_store.delete(session_id)