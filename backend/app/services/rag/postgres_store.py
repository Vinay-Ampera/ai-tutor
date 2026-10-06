import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.services.rag.embeddings import EMBEDDING_DIMENSION
from app.services.rag.markdown_loader import MarkdownSource

logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[3]


class DatabaseConfigurationError(RuntimeError):
    pass


class DatabasePersistenceError(RuntimeError):
    pass


def connect_database() -> psycopg.Connection:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env")
    settings = {
        "DB_HOST": os.getenv("DB_HOST", "").strip(),
        "DB_PORT": os.getenv("DB_PORT", "").strip(),
        "DB_NAME": os.getenv("DB_NAME", "").strip(),
        "DB_USER": os.getenv("DB_USER", "").strip(),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
    }
    missing_settings = [
        setting for setting, value in settings.items() if not value
    ]
    if missing_settings:
        raise DatabaseConfigurationError(
            "Set DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD "
            "in backend/.env to connect to PostgreSQL."
        )
    try:
        port = int(settings["DB_PORT"])
    except ValueError as error:
        raise DatabaseConfigurationError(
            "DB_PORT in backend/.env must be a valid TCP port number."
        ) from error
    if not 1 <= port <= 65535:
        raise DatabaseConfigurationError(
            "DB_PORT in backend/.env must be between 1 and 65535."
        )
    try:
        return psycopg.connect(
            host=settings["DB_HOST"],
            port=port,
            dbname=settings["DB_NAME"],
            user=settings["DB_USER"],
            password=settings["DB_PASSWORD"],
            row_factory=dict_row,
        )
    except psycopg.Error as error:
        logger.error(
            "Could not connect to the PostgreSQL RAG database (%s).",
            type(error).__name__,
        )
        raise DatabaseConfigurationError(
            "Could not connect to PostgreSQL. Check DB_HOST, DB_PORT, "
            "DB_NAME, DB_USER, and database availability."
        ) from error


def ensure_rag_schema(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        if not cursor.fetchone()["exists"]:
            raise DatabaseConfigurationError(
                "The PostgreSQL vector extension is not enabled in the selected database."
            )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_documents (
                id UUID PRIMARY KEY,
                owner_id UUID NULL,
                original_filename TEXT NOT NULL,
                source_format TEXT NOT NULL,
                markdown_filename TEXT,
                markdown_path TEXT UNIQUE,
                uploaded_at TIMESTAMPTZ NOT NULL,
                processing_status TEXT NOT NULL DEFAULT 'INDEXED',
                session_id TEXT,
                processing_error TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                indexed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute(
            """
            ALTER TABLE rag_documents
                ALTER COLUMN markdown_filename DROP NOT NULL,
                ALTER COLUMN markdown_path DROP NOT NULL,
                ADD COLUMN IF NOT EXISTS session_id TEXT,
                ADD COLUMN IF NOT EXISTS processing_error TEXT
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS rag_documents_session_id_idx
            ON rag_documents (session_id)
            WHERE session_id IS NOT NULL
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS rag_document_chunks (
                id UUID PRIMARY KEY,
                document_id UUID NOT NULL
                    REFERENCES rag_documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding vector({EMBEDDING_DIMENSION}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (document_id, chunk_index)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS rag_chunks_document_id_idx
            ON rag_document_chunks (document_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS rag_chunks_embedding_hnsw_idx
            ON rag_document_chunks
            USING hnsw (embedding vector_cosine_ops)
            """
        )
    register_vector(connection)


def store_document_chunks(
    source: MarkdownSource,
    chunks: list[tuple[str, dict[str, object]]],
    embeddings: list[list[float]],
    *,
    document_id: UUID | None = None,
    ready_status: str = "INDEXED",
) -> tuple[UUID, int]:
    if len(chunks) != len(embeddings) or not chunks:
        raise ValueError("Every stored chunk must have exactly one embedding.")
    if any(len(vector) != EMBEDDING_DIMENSION for vector in embeddings):
        raise ValueError(
            f"Every embedding must contain {EMBEDDING_DIMENSION} dimensions."
        )

    try:
        with connect_database() as connection:
            ensure_rag_schema(connection)
            with connection.cursor() as cursor:
                if document_id is None:
                    cursor.execute(
                        "SELECT id FROM rag_documents WHERE markdown_path = %s",
                        (source.markdown_path,),
                    )
                else:
                    cursor.execute(
                        "SELECT id FROM rag_documents WHERE id = %s",
                        (document_id,),
                    )
                existing = cursor.fetchone()
                if document_id is not None and existing is None:
                    raise DatabasePersistenceError(
                        "The document processing record no longer exists."
                    )
                document_id = existing["id"] if existing else uuid4()
                if existing:
                    cursor.execute(
                        """
                        UPDATE rag_documents
                        SET original_filename = %s,
                            source_format = %s,
                            markdown_filename = %s,
                            markdown_path = %s,
                            uploaded_at = %s,
                            processing_status = 'INDEXING',
                            processing_error = NULL,
                            indexed_at = now()
                        WHERE id = %s
                        """,
                        (
                            source.original_filename,
                            source.source_format,
                            source.markdown_filename,
                            source.markdown_path,
                            source.uploaded_at,
                            document_id,
                        ),
                    )
                    cursor.execute(
                        "DELETE FROM rag_document_chunks WHERE document_id = %s",
                        (document_id,),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO rag_documents (
                            id, original_filename, source_format, markdown_filename,
                            markdown_path, uploaded_at, processing_status, session_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 'INDEXING', NULL)
                        """,
                        (
                            document_id,
                            source.original_filename,
                            source.source_format,
                            source.markdown_filename,
                            source.markdown_path,
                            source.uploaded_at,
                        ),
                    )

                cursor.executemany(
                    """
                    INSERT INTO rag_document_chunks (
                        id, document_id, chunk_index, content, metadata, embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            uuid4(),
                            document_id,
                            index,
                            content,
                            Jsonb(metadata),
                            Vector(embedding),
                        )
                        for index, ((content, metadata), embedding)
                        in enumerate(zip(chunks, embeddings, strict=True))
                    ],
                )
                cursor.execute(
                    """
                    SELECT count(*) AS chunk_count,
                           min(vector_dims(embedding)) AS minimum_dimension,
                           max(vector_dims(embedding)) AS maximum_dimension
                    FROM rag_document_chunks
                    WHERE document_id = %s
                    """,
                    (document_id,),
                )
                verification = cursor.fetchone()
                if (
                    verification["chunk_count"] != len(chunks)
                    or verification["minimum_dimension"] != EMBEDDING_DIMENSION
                    or verification["maximum_dimension"] != EMBEDDING_DIMENSION
                ):
                    raise DatabasePersistenceError(
                        "PostgreSQL verification found incomplete or invalid vectors."
                    )
                cursor.execute(
                    """
                    UPDATE rag_documents
                    SET processing_status = %s, processing_error = NULL,
                        indexed_at = now()
                    WHERE id = %s
                    """,
                    (ready_status, document_id),
                )
        return document_id, len(chunks)
    except psycopg.Error as error:
        logger.error(
            "Could not store document chunks in PostgreSQL (%s).",
            type(error).__name__,
        )
        raise DatabasePersistenceError(
            "PostgreSQL failed while saving or verifying document chunks."
        ) from error


def start_session_document_processing(
    session_id: str,
    original_filename: str,
    source_format: str,
) -> UUID:
    document_id = uuid4()
    try:
        with connect_database() as connection:
            ensure_rag_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM rag_documents WHERE session_id = %s",
                    (session_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO rag_documents (
                        id, session_id, original_filename, source_format,
                        uploaded_at, processing_status
                    )
                    VALUES (%s, %s, %s, %s, now(), 'PROCESSING')
                    """,
                    (document_id, session_id, original_filename, source_format),
                )
        return document_id
    except psycopg.Error as error:
        logger.error(
            "Could not start document processing in PostgreSQL (%s).",
            type(error).__name__,
        )
        raise DatabasePersistenceError(
            "PostgreSQL failed while starting document processing."
        ) from error


def mark_session_document_failed(document_id: UUID, reason: str) -> None:
    try:
        with connect_database() as connection:
            ensure_rag_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE rag_documents
                    SET processing_status = 'FAILED', processing_error = %s
                    WHERE id = %s
                    """,
                    (reason[:1000], document_id),
                )
    except psycopg.Error as error:
        logger.error(
            "Could not record failed document processing (%s).",
            type(error).__name__,
        )
        raise DatabasePersistenceError(
            "PostgreSQL failed while recording the document processing error."
        ) from error


def session_document_status(session_id: str) -> dict[str, object] | None:
    try:
        with connect_database() as connection:
            ensure_rag_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, original_filename, processing_status,
                           processing_error, markdown_filename, indexed_at
                    FROM rag_documents
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
                return cursor.fetchone()
    except psycopg.Error as error:
        logger.error(
            "Could not look up session document status (%s).",
            type(error).__name__,
        )
        raise DatabasePersistenceError(
            "PostgreSQL failed while checking document processing status."
        ) from error


def latest_indexed_document(
    session_id: str | None = None,
) -> dict[str, object] | None:
    try:
        with connect_database() as connection:
            with connection.cursor() as cursor:
                if session_id is None:
                    cursor.execute(
                        """
                        SELECT id, original_filename, markdown_filename
                        FROM rag_documents
                        WHERE processing_status IN ('INDEXED', 'READY')
                        ORDER BY indexed_at DESC, created_at DESC
                        LIMIT 1
                        """
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, original_filename, markdown_filename
                        FROM rag_documents
                        WHERE session_id = %s
                          AND processing_status = 'READY'
                        ORDER BY indexed_at DESC, created_at DESC
                        LIMIT 1
                        """,
                        (session_id,),
                    )
                return cursor.fetchone()
    except psycopg.Error as error:
        logger.error(
            "Could not look up indexed documents in PostgreSQL (%s).",
            type(error).__name__,
        )
        raise DatabasePersistenceError(
            "PostgreSQL failed while checking for an indexed document."
        ) from error


def search_similar_chunks(
    query_embedding: list[float],
    *,
    limit: int = 5,
    document_id: UUID | None = None,
) -> list[dict[str, object]]:
    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Query embeddings must contain {EMBEDDING_DIMENSION} dimensions."
        )
    if limit < 1 or limit > 100:
        raise ValueError("Search limit must be between 1 and 100.")

    try:
        with connect_database() as connection:
            register_vector(connection)
            with connection.cursor() as cursor:
                if document_id is None:
                    cursor.execute(
                        """
                        SELECT document_id, content, metadata,
                               1 - (embedding <=> %s) AS similarity
                        FROM rag_document_chunks
                        ORDER BY embedding <=> %s
                        LIMIT %s
                        """,
                        (Vector(query_embedding), Vector(query_embedding), limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT chunks.document_id, chunks.content, chunks.metadata,
                               1 - (embedding <=> %s) AS similarity
                        FROM rag_document_chunks AS chunks
                        JOIN rag_documents AS documents
                          ON documents.id = chunks.document_id
                        WHERE chunks.document_id = %s
                          AND documents.processing_status IN ('INDEXED', 'READY')
                        ORDER BY chunks.embedding <=> %s
                        LIMIT %s
                        """,
                        (
                            Vector(query_embedding),
                            document_id,
                            Vector(query_embedding),
                            limit,
                        ),
                    )
                return list(cursor.fetchall())
    except psycopg.Error as error:
        logger.error(
            "PostgreSQL vector search failed (%s).",
            type(error).__name__,
        )
        raise DatabasePersistenceError(
            "PostgreSQL failed while searching document vectors."
        ) from error
