from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.graphs.tutor_graph import run_tutor_graph
from app.graphs.tutor_state import TutorAction
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
    allow_methods=["GET", "POST"],
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


@app.get("/")
def root():
    return {"message": "AI Tutor API is running"}


@app.post("/api/gemini/generate", response_model=GeminiResponse)
def generate_gemini_response(request: GeminiRequest) -> GeminiResponse:
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt must not be empty.")

    try:
        result = run_tutor_graph(
            request.prompt,
            request.session_id,
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
        )
    except GeminiQuotaError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except GeminiConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except GeminiRequestError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return GeminiResponse(text=result["response"])