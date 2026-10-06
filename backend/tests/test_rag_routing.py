import json
import unittest
from uuid import uuid4
from unittest.mock import patch

from app.graphs.retrieval_nodes import TOP_K_DOCUMENT_CHUNKS
from app.graphs.tutor_graph import run_tutor_graph
from app.services.gemini import GeminiConfigurationError
from app.services.rag.postgres_store import DatabaseConfigurationError
from fastapi.testclient import TestClient
from app.main import app


def classification(category: str) -> str:
    flags = {
        "greeting": (True, False),
        "educational": (False, True),
        "out_of_scope": (False, False),
    }[category]
    return json.dumps(
        {
            "request_category": category,
            "is_greeting": flags[0],
            "is_educational": flags[1],
        }
    )


class RagRoutingTests(unittest.TestCase):
    def test_normal_educational_questions_keep_existing_tutor_path(self) -> None:
        with (
            patch(
                "app.services.gemini.generate_text",
                side_effect=[
                    classification("educational"),
                    json.dumps(
                        {
                            "topic": "Photosynthesis",
                            "student_level": "beginner",
                            "teaching_approach": "Explain the process simply.",
                        }
                    ),
                    "Plants convert light energy into chemical energy.",
                    "A plant uses sunlight like a small solar-powered kitchen.",
                ],
            ),
            patch(
                "app.graphs.retrieval_nodes.session_document_status"
            ) as ready_lookup,
            patch("app.graphs.retrieval_nodes.embed_query") as embed_query,
        ):
            result = run_tutor_graph(
                "Explain photosynthesis.",
                session_id=f"normal-{uuid4().hex}",
            )

        self.assertEqual(result["next_action"], "teaching")
        self.assertIn("Plants convert light energy", result["response"])
        ready_lookup.assert_not_called()
        embed_query.assert_not_called()

    def test_document_question_without_indexed_document_returns_not_ready(self) -> None:
        with (
            patch(
                "app.services.gemini.generate_text",
                return_value=classification("educational"),
            ) as generate_text,
            patch(
                "app.graphs.retrieval_nodes.session_document_status",
                return_value=None,
            ),
            patch("app.graphs.retrieval_nodes.embed_query") as embed_query,
            patch(
                "app.graphs.retrieval_nodes.search_similar_chunks"
            ) as vector_search,
        ):
            result = run_tutor_graph(
                "According to the uploaded document, what is photosynthesis?",
                session_id=f"not-ready-{uuid4().hex}",
            )

        self.assertEqual(result["next_action"], "document_not_ready")
        self.assertIn("No indexed document is ready", result["response"])
        self.assertEqual(generate_text.call_count, 1)
        embed_query.assert_not_called()
        vector_search.assert_not_called()

    def test_ready_document_question_embeds_retrieves_and_generates_grounded_answer(
        self,
    ) -> None:
        document_id = uuid4()
        query_vector = [0.25] * 384
        chunks = [
            {
                "content": "Photosynthesis converts light into chemical energy.",
                "metadata": {"heading": "Plant energy", "page_number": 2},
                "similarity": 0.87,
            }
        ]
        with (
            patch(
                "app.services.gemini.generate_text",
                side_effect=[
                    classification("educational"),
                    "The document says photosynthesis converts light into "
                    "chemical energy (page 2).",
                ],
            ) as generate_text,
            patch(
                "app.graphs.retrieval_nodes.session_document_status",
                return_value={
                    "id": document_id,
                    "original_filename": "biology.pdf",
                    "processing_status": "READY",
                },
            ),
            patch(
                "app.graphs.retrieval_nodes.embed_query",
                return_value=query_vector,
            ) as embed_query,
            patch(
                "app.graphs.retrieval_nodes.search_similar_chunks",
                return_value=chunks,
            ) as vector_search,
        ):
            result = run_tutor_graph(
                "According to the uploaded document, what does photosynthesis do?",
                session_id=f"ready-{uuid4().hex}",
            )

        self.assertEqual(result["next_action"], "document_answer")
        self.assertEqual(result["retrieved_chunks"][0]["metadata"]["page_number"], 2)
        self.assertIn("converts light into chemical energy", result["response"])
        embed_query.assert_called_once_with(
            "According to the uploaded document, what does photosynthesis do?"
        )
        vector_search.assert_called_once_with(
            query_vector,
            document_id=document_id,
            limit=TOP_K_DOCUMENT_CHUNKS,
        )
        grounding_prompt = generate_text.call_args.args[0]
        self.assertIn("using only the retrieved document", grounding_prompt)
        self.assertIn("Photosynthesis converts light into chemical energy.", grounding_prompt)
        self.assertIn("biology.pdf", grounding_prompt)

    def test_empty_retrieval_returns_document_not_found_without_generation(self) -> None:
        with (
            patch(
                "app.services.gemini.generate_text",
                return_value=classification("educational"),
            ) as generate_text,
            patch(
                "app.graphs.retrieval_nodes.session_document_status",
                return_value={
                    "id": uuid4(),
                    "original_filename": "biology.pdf",
                    "processing_status": "READY",
                },
            ),
            patch(
                "app.graphs.retrieval_nodes.embed_query",
                return_value=[0.0] * 384,
            ),
            patch(
                "app.graphs.retrieval_nodes.search_similar_chunks",
                return_value=[],
            ),
        ):
            result = run_tutor_graph(
                "What does the uploaded document say about mitochondria?",
                session_id=f"no-match-{uuid4().hex}",
            )

        self.assertIn("could not find supporting information", result["response"])
        self.assertEqual(result["next_action"], "document_not_found")
        generate_text.assert_called_once()

    def test_out_of_scope_document_request_does_not_check_readiness_or_retrieve(
        self,
    ) -> None:
        with (
            patch(
                "app.services.gemini.generate_text",
                return_value=classification("out_of_scope"),
            ),
            patch(
                "app.graphs.retrieval_nodes.session_document_status"
            ) as ready_lookup,
            patch("app.graphs.retrieval_nodes.embed_query") as embed_query,
        ):
            result = run_tutor_graph(
                "Use the uploaded document to write me a sales proposal.",
                session_id=f"scope-{uuid4().hex}",
            )

        self.assertEqual(result["next_action"], "refusal")
        ready_lookup.assert_not_called()
        embed_query.assert_not_called()

    def test_database_configuration_error_propagates_as_configuration_failure(
        self,
    ) -> None:
        with (
            patch(
                "app.services.gemini.generate_text",
                return_value=classification("educational"),
            ),
            patch(
                "app.graphs.retrieval_nodes.session_document_status",
                side_effect=DatabaseConfigurationError("Database unavailable."),
            ),
        ):
            with self.assertRaises(GeminiConfigurationError):
                run_tutor_graph(
                    "According to the uploaded document, explain cell division.",
                    session_id=f"db-error-{uuid4().hex}",
                )

    def test_database_configuration_failure_is_reported_as_api_503(self) -> None:
        with (
            TestClient(app) as client,
            patch(
                "app.services.gemini.generate_text",
                return_value=classification("educational"),
            ),
            patch(
                "app.graphs.retrieval_nodes.session_document_status",
                side_effect=DatabaseConfigurationError("Database unavailable."),
            ),
        ):
            response = client.post(
                "/api/gemini/generate",
                json={
                    "prompt": "According to the uploaded document, explain cells.",
                    "session_id": f"api-db-error-{uuid4().hex}",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Database unavailable.")
