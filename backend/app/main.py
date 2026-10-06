from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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
from app.services.document_ingestion import (
    DocumentIngestionError,
    DocumentStorageError,
    SUPPORTED_FORMATS,
    UnsupportedDocumentFormatError,
    ingest_document,
)
from app.services.rag.embeddings import (
    EMBEDDING_DIMENSION,
    EmbeddingModelError,
)
from app.services.rag.indexing import index_stage10_markdown
from app.services.rag.markdown_loader import MarkdownDocumentError
from app.services.rag.postgres_store import (
    DatabaseConfigurationError,
    DatabasePersistenceError,
    mark_session_document_failed,
    session_document_status,
    start_session_document_processing,
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


class DocumentMetadataResponse(BaseModel):
    original_filename: str
    file_type: str
    processed_at: str
    markdown_filename: str
    markdown_path: str


class DocumentIngestionResponse(BaseModel):
    message: str
    metadata: DocumentMetadataResponse


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: str
    processing_status: str
    chunk_count: int
    embedding_dimension: int
    metadata: DocumentMetadataResponse


class SessionDocumentStatusResponse(BaseModel):
    processing_status: str
    original_filename: str | None = None
    processing_error: str | None = None
    markdown_filename: str | None = None


class DocumentIndexRequest(BaseModel):
    markdown_filename: str = Field(min_length=1, max_length=255)


class DocumentIndexResponse(BaseModel):
    document_id: str
    original_filename: str
    source_format: str
    markdown_filename: str
    markdown_path: str
    chunk_count: int
    embedding_dimension: int
    processing_status: str


@app.get("/")
def root():
    return {
        "message": "AI Tutor API is running",
        "server_instance_id": SERVER_INSTANCE_ID,
    }


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> None:
    clear_tutor_session(session_id)


@app.get(
    "/api/sessions/{session_id}/document",
    response_model=SessionDocumentStatusResponse,
)
def get_session_document_status(session_id: str) -> SessionDocumentStatusResponse:
    try:
        status = session_document_status(session_id)
    except DatabaseConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except DatabasePersistenceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if status is None:
        return SessionDocumentStatusResponse(processing_status="EMPTY")
    return SessionDocumentStatusResponse(
        processing_status=str(status["processing_status"]),
        original_filename=str(status["original_filename"]),
        processing_error=(
            str(status["processing_error"])
            if status["processing_error"] is not None
            else None
        ),
        markdown_filename=(
            str(status["markdown_filename"])
            if status["markdown_filename"] is not None
            else None
        ),
    )


@app.post(
    "/api/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
)
async def upload_and_prepare_document(
    session_id: str = Form(min_length=1, max_length=100),
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    if not file.filename or not file.filename.strip():
        raise HTTPException(status_code=422, detail="A filename is required.")

    file_type = Path(file.filename.replace("\\", "/")).suffix.lower().lstrip(".")
    if file_type not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format. Upload a PDF, DOCX, XLS, or XLSX file.",
        )

    content = await file.read()
    await file.close()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    try:
        document_id = start_session_document_processing(
            session_id,
            file.filename,
            file_type,
        )
    except DatabaseConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except DatabasePersistenceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        ingestion = ingest_document(file.filename, content)
        indexed = index_stage10_markdown(
            ingestion.markdown_filename,
            document_id=document_id,
            ready_status="READY",
        )
    except (
        UnsupportedDocumentFormatError,
        DocumentIngestionError,
        DocumentStorageError,
        MarkdownDocumentError,
        EmbeddingModelError,
        DatabaseConfigurationError,
        DatabasePersistenceError,
        ValueError,
    ) as error:
        try:
            mark_session_document_failed(document_id, str(error))
        except (DatabaseConfigurationError, DatabasePersistenceError) as status_error:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Document processing failed and its status could not be saved. "
                    f"{status_error}"
                ),
            ) from status_error
        if isinstance(error, UnsupportedDocumentFormatError):
            raise HTTPException(status_code=415, detail=str(error)) from error
        if isinstance(error, (DocumentIngestionError, MarkdownDocumentError, ValueError)):
            raise HTTPException(status_code=422, detail=str(error)) from error
        if isinstance(error, DocumentStorageError):
            raise HTTPException(
                status_code=500,
                detail="The processed Markdown could not be saved.",
            ) from error
        raise HTTPException(status_code=503, detail=str(error)) from error

    return DocumentUploadResponse(
        message="Your document is ready. You can ask questions about it.",
        document_id=str(indexed.document_id),
        processing_status=indexed.processing_status,
        chunk_count=indexed.chunk_count,
        embedding_dimension=indexed.embedding_dimension,
        metadata=DocumentMetadataResponse(
            original_filename=ingestion.original_filename,
            file_type=ingestion.file_type,
            processed_at=ingestion.processed_at,
            markdown_filename=ingestion.markdown_filename,
            markdown_path=ingestion.markdown_path,
        ),
    )


@app.post(
    "/api/documents/ingest",
    response_model=DocumentIngestionResponse,
    status_code=201,
)
async def ingest_uploaded_document(
    file: UploadFile = File(...),
) -> DocumentIngestionResponse:
    if not file.filename or not file.filename.strip():
        raise HTTPException(status_code=422, detail="A filename is required.")

    content = await file.read()
    await file.close()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    try:
        result = ingest_document(file.filename, content)
    except UnsupportedDocumentFormatError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except DocumentIngestionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DocumentStorageError as error:
        raise HTTPException(
            status_code=500,
            detail="The processed Markdown could not be saved.",
        ) from error

    return DocumentIngestionResponse(
        message="Document parsed and saved as Markdown.",
        metadata=DocumentMetadataResponse(
            original_filename=result.original_filename,
            file_type=result.file_type,
            processed_at=result.processed_at,
            markdown_filename=result.markdown_filename,
            markdown_path=result.markdown_path,
        ),
    )


@app.post(
    "/api/documents/index",
    response_model=DocumentIndexResponse,
    status_code=201,
)
def index_markdown_document(
    request: DocumentIndexRequest,
) -> DocumentIndexResponse:
    try:
        result = index_stage10_markdown(request.markdown_filename)
    except MarkdownDocumentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except EmbeddingModelError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except DatabaseConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except DatabasePersistenceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return DocumentIndexResponse(
        document_id=str(result.document_id),
        original_filename=result.original_filename,
        source_format=result.source_format,
        markdown_filename=result.markdown_filename,
        markdown_path=result.markdown_path,
        chunk_count=result.chunk_count,
        embedding_dimension=EMBEDDING_DIMENSION,
        processing_status=result.processing_status,
    )


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