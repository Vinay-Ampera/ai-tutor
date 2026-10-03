import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_MODEL = "gemini-3.5-flash-lite"


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiRequestError(RuntimeError):
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
    try:
        with genai.Client(api_key=api_key) as client:
            response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        if getattr(exc, "code", None) == 429:
            raise GeminiQuotaError(
                "The tutor has reached its current AI request quota. "
                "Please try again later or check the Gemini API quota and billing settings."
            ) from exc
        raise GeminiRequestError("Gemini generation failed.") from exc

    text = response.text
    if not text or not text.strip():
        raise GeminiRequestError("Gemini returned an empty response.")

    return text.strip()