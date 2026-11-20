""" wrapper around the llm api
    only module responsible with LLM provider handling
"""
import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
MAX_RETRIES = 3


class LLMError(Exception):
    """An LLM failure the UI should show to the user in a friendly way."""


_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not os.environ.get("GEMINI_API_KEY"):
            raise LLMError("GEMINI_API_KEY is not set. Add it to your .env file.")
        _client = genai.Client()
    return _client


def _to_gemini(messages: list[dict]) -> list[types.Content]:
    """Convert our neutral format {"role": "user"|"assistant", "content": str}."""
    return [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]


def _call(system: str, messages: list[dict], temperature: float, json_mode: bool) -> str:
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    for attempt in range(MAX_RETRIES):
        try:
            resp = _get_client().models.generate_content(
                model=MODEL, contents=_to_gemini(messages), config=config
            )
        except errors.APIError as e:
            retryable = e.code == 429 or (e.code or 0) >= 500
            if retryable and attempt < MAX_RETRIES - 1:
                time.sleep(2 * 2**attempt)  # 2s, then 4s
                continue
            raise LLMError(f"Gemini API error ({e.code}): {e.message}") from e
        if not resp.text:
            raise LLMError("The model returned an empty response.")
        return resp.text.strip()


def chat(system: str, messages: list[dict], temperature: float = 0.7) -> str:
    """Free-text reply given a conversation history."""
    return _call(system, messages, temperature, json_mode=False)


def generate_json(system: str, prompt: str, temperature: float = 0.3) -> dict:
    """Structured reply, parsed as JSON. Retries once on malformed output."""
    messages = [{"role": "user", "content": prompt}]
    for _ in range(2):
        raw = _call(system, messages, temperature, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    raise LLMError("The model did not return valid JSON.")


if __name__ == "__main__":
    print(chat("You are terse.", [{"role": "user", "content": "Say hi in 5 words."}]))
    print(generate_json("Reply in JSON.", 'Return {"ok": true, "n": 3}'))