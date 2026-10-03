import unittest
from unittest.mock import MagicMock, patch

import httpx
from google.genai.errors import ClientError

from app.services.gemini import (
    DEFAULT_MODEL,
    GeminiConfigurationError,
    GeminiRequestError,
    generate_text,
)


class GeminiServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.http_client = MagicMock()
        self.http_client_context = MagicMock()
        self.http_client_context.__enter__.return_value = self.http_client
        self.api_client = MagicMock()
        self.api_client_context = MagicMock()
        self.api_client_context.__enter__.return_value = self.api_client
        self.api_client.models.generate_content.return_value.text = "Tutor response"

    def test_uses_available_default_model_and_ipv4_transport(self) -> None:
        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "test-key"},
            clear=True,
        ):
            with patch(
                "app.services.gemini.httpx.HTTPTransport",
                wraps=httpx.HTTPTransport,
            ) as transport_factory:
                with patch(
                    "app.services.gemini.genai.Client",
                    return_value=self.api_client_context,
                ) as api_client_factory:
                    result = generate_text("  Explain a concept  ")

        self.assertEqual(result, "Tutor response")
        self.assertEqual(DEFAULT_MODEL, "gemini-3.1-flash-lite")
        transport_factory.assert_called_once_with(local_address="0.0.0.0")
        options = api_client_factory.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, 30_000)
        self.assertIsInstance(options.httpx_client, httpx.Client)
        self.api_client.models.generate_content.assert_called_once_with(
            model=DEFAULT_MODEL,
            contents="Explain a concept",
        )

    def test_unavailable_model_returns_actionable_configuration_error(self) -> None:
        self.api_client.models.generate_content.side_effect = ClientError(
            404,
            {"error": {"message": "model unavailable"}},
        )
        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "old-model"},
            clear=True,
        ):
            with patch(
                "app.services.gemini.genai.Client",
                return_value=self.api_client_context,
            ):
                with self.assertRaisesRegex(
                    GeminiConfigurationError,
                    "old-model.*gemini-3.1-flash-lite",
                ):
                    generate_text("Explain a concept")

    def test_http_timeout_is_reported_as_request_error(self) -> None:
        self.api_client.models.generate_content.side_effect = httpx.ReadTimeout(
            "request timed out"
        )
        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "test-key"},
            clear=True,
        ):
            with patch(
                "app.services.gemini.genai.Client",
                return_value=self.api_client_context,
            ):
                with self.assertRaisesRegex(
                    GeminiRequestError,
                    "did not respond within 30 seconds",
                ):
                    generate_text("Explain a concept")

    def test_unavailable_model_configuration_error_is_a_request_error(self) -> None:
        self.assertIsInstance(
            GeminiConfigurationError("Model unavailable"),
            GeminiRequestError,
        )
