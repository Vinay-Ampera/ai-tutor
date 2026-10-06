from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384


class EmbeddingModelError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME, device="cpu")
    except (OSError, RuntimeError, ValueError) as error:
        raise EmbeddingModelError(
            f"Could not load the local embedding model {MODEL_NAME}."
        ) from error

    actual_dimension = model.get_embedding_dimension()
    if actual_dimension != EMBEDDING_DIMENSION:
        raise EmbeddingModelError(
            f"{MODEL_NAME} returned dimension {actual_dimension}; "
            f"expected {EMBEDDING_DIMENSION}."
        )
    return model


def count_embedding_tokens(text: str) -> int:
    model = _load_model()
    return len(model.tokenizer(text, add_special_tokens=True)["input_ids"])


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if any(not text.strip() for text in texts):
        raise ValueError("Embedding input must not contain empty text.")

    model = _load_model()
    try:
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except (OSError, RuntimeError, ValueError) as error:
        raise EmbeddingModelError(
            f"Local embedding generation failed with {MODEL_NAME}."
        ) from error

    array = np.asarray(vectors, dtype=np.float32)
    if array.shape != (len(texts), EMBEDDING_DIMENSION):
        raise EmbeddingModelError(
            f"{MODEL_NAME} returned embedding shape {array.shape}; "
            f"expected ({len(texts)}, {EMBEDDING_DIMENSION})."
        )
    if not np.isfinite(array).all():
        raise EmbeddingModelError(f"{MODEL_NAME} returned a non-finite embedding.")
    return array.tolist()


def embed_query(query: str) -> list[float]:
    if not query.strip():
        raise ValueError("Query must not be empty.")
    return embed_texts([query])[0]
