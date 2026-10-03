import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.1-flash-lite"
REQUEST_TIMEOUT_SECONDS = 30


class GeminiRequestError(RuntimeError):
    pass


class GeminiConfigurationError(GeminiRequestError):
    pass


class GeminiQuotaError(GeminiRequestError):
    pass


def generate_text(prompt: str) -> str:
    """Generate text with Gemini using backend-only environment configuration."""
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt must not be empty.")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.lower() == "your_api_key_here":
        raise GeminiConfigurationError(
            "Set a valid GEMINI_API_KEY in backend/.env before calling Gemini."
        )

    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    force_ipv4 = os.getenv("GEMINI_IPV4_ONLY", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    transport = (
        httpx.HTTPTransport(local_address="0.0.0.0") if force_ipv4 else None
    )
    try:
        with httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(
                REQUEST_TIMEOUT_SECONDS,
                connect=10,
            ),
        ) as http_client:
            with genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=REQUEST_TIMEOUT_SECONDS * 1000,
                    httpx_client=http_client,
                ),
            ) as client:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
    except Exception as exc:
        if getattr(exc, "code", None) == 429:
            raise GeminiQuotaError(
                "The tutor has reached its current AI request quota. "
                "Please try again later or check the Gemini API quota and billing settings."
            ) from exc
        if getattr(exc, "code", None) == 404:
            logger.error("Gemini model %s is unavailable to this API key.", model)
            raise GeminiConfigurationError(
                f"Gemini model '{model}' is unavailable to this API key. "
                f"Set GEMINI_MODEL to a supported model, such as {DEFAULT_MODEL}."
            ) from exc
        if isinstance(exc, httpx.TimeoutException):
            logger.warning("Gemini request timed out using model %s.", model)
            raise GeminiRequestError(
                f"Gemini did not respond within {REQUEST_TIMEOUT_SECONDS} seconds."
            ) from exc
        logger.exception("Gemini request failed using model %s.", model)
        raise GeminiRequestError(
            f"Gemini generation failed using model '{model}'. "
            "Check backend logs for the provider error."
        ) from exc

    text = response.text
    if not text or not text.strip():
        raise GeminiRequestError("Gemini returned an empty response.")

    return text.strip()