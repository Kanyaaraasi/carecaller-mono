import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, RateLimitError, APIStatusError

from .base import LLMProvider, LLMResponse

# Load .env from project root
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)

# Rate limit config
MAX_RETRIES = 5
BASE_BACKOFF = 2.0  # seconds
REQUEST_DELAY = 0.5  # minimum delay between requests (seconds)


class GroqProvider(LLMProvider):
    """Groq Cloud LLM provider with rate limiting and retry logic."""

    def __init__(self, model: str | None = None):
        super().__init__(model or "openai/gpt-oss-120b")
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Set it in .env or environment.")
        self.client = Groq(api_key=api_key)
        self._last_request_time = 0.0

    def _throttle(self):
        """Enforce minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _call_with_retry(self, messages: list, temperature: float,
                         max_tokens: int, response_format: dict | None = None):
        """Make API call with exponential backoff on rate limits."""
        for attempt in range(MAX_RETRIES):
            self._throttle()
            try:
                kwargs = dict(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if response_format:
                    kwargs["response_format"] = response_format
                return self.client.chat.completions.create(**kwargs)

            except RateLimitError as e:
                wait = BASE_BACKOFF * (2 ** attempt)
                # Check for retry-after header hint
                retry_after = getattr(e, "retry_after", None)
                if retry_after:
                    wait = max(wait, float(retry_after))
                print(f"    Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait:.1f}s...")
                time.sleep(wait)

            except APIStatusError as e:
                if e.status_code == 503:
                    wait = BASE_BACKOFF * (2 ** attempt)
                    print(f"    Service unavailable (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError(f"Failed after {MAX_RETRIES} retries")

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self._call_with_retry(messages, temperature=0.1, max_tokens=2048)
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content,
            model=resp.model,
            usage={
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
            } if resp.usage else None,
        )

    def complete_json(self, prompt: str, system: str = "") -> dict:
        messages = []
        sys_msg = (system + "\n\n" if system else "") + "Respond ONLY with valid JSON. No markdown, no explanation."
        messages.append({"role": "system", "content": sys_msg})
        messages.append({"role": "user", "content": prompt})

        resp = self._call_with_retry(
            messages, temperature=0.0, max_tokens=2048,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        return json.loads(raw)
