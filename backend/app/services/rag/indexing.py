from dataclasses import dataclass
from uuid import UUID

from app.services.rag.chunking import chunk_markdown
from app.services.rag.embeddings import (
    EMBEDDING_DIMENSION,
    count_embedding_tokens,
    embed_texts,
)
from app.services.rag.markdown_loader import load_stage10_markdown
from app.services.rag.postgres_store import store_document_chunks


@dataclass(frozen=True)
class IndexingResult:
    document_id: UUID
    original_filename: str
    source_format: str
    markdown_filename: str
    markdown_path: str
    chunk_count: int
    embedding_dimension: int
    processing_status: str


def index_stage10_markdown(markdown_filename: str) -> IndexingResult:
    source = load_stage10_markdown(markdown_filename)
    chunks = chunk_markdown(
        source.content,
        token_counter=count_embedding_tokens,
    )
    if not chunks:
        raise ValueError("No indexable text was found in the Markdown document.")

    vectors = embed_texts([chunk.content for chunk in chunks])
    document_id, stored_chunk_count = store_document_chunks(
        source,
        [(chunk.content, chunk.metadata()) for chunk in chunks],
        vectors,
    )
    return IndexingResult(
        document_id=document_id,
        original_filename=source.original_filename,
        source_format=source.source_format,
        markdown_filename=source.markdown_filename,
        markdown_path=source.markdown_path,
        chunk_count=stored_chunk_count,
        embedding_dimension=EMBEDDING_DIMENSION,
        processing_status="INDEXED",
    )
