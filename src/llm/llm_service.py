"""Configurable local-Ollama or OpenAI LLM service with safe failure modes."""

import os
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

try:
    from .prompts import SYSTEM_PROMPT, build_user_prompt
except ImportError:
    from prompts import SYSTEM_PROMPT, build_user_prompt


class LLMServiceError(RuntimeError):
    """A user-safe failure that the later API layer can handle."""


class LLMService:
    def __init__(self):
        load_dotenv()
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "llama3.2:latest")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "300"))
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434").rstrip("/")
        self.client = None
        if self.provider == "openai":
            if not self.api_key or self.api_key == "your_api_key_here":
                raise LLMServiceError("LLM_API_KEY is not configured. Add a valid key to .env.")
            options = {"api_key": self.api_key}
            if self.base_url and "localhost" not in self.base_url:
                options["base_url"] = self.base_url
            self.client = OpenAI(**options)
        elif self.provider != "ollama":
            raise LLMServiceError(f"Unsupported LLM_PROVIDER: {self.provider}. Configure 'ollama' or 'openai'.")

    def generate_response(self, customer_email, category, context):
        """Generate one grounded answer; no fallback response is invented on failure."""
        if self.provider == "ollama":
            return self._generate_with_ollama(customer_email, category, context)
        return self._generate_with_openai(customer_email, category, context)

    def _generate_with_openai(self, customer_email, category, context):
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=build_user_prompt(customer_email["subject"], customer_email["email_body"], category, context),
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                store=False,
            )
            text = (response.output_text or "").strip()
            if not text:
                raise LLMServiceError("The LLM returned an empty response.")
            return text
        except AuthenticationError as error:
            raise LLMServiceError("LLM authentication failed. Check LLM_API_KEY.") from error
        except RateLimitError as error:
            raise LLMServiceError("LLM rate limit reached. Try again later.") from error
        except APITimeoutError as error:
            raise LLMServiceError("LLM request timed out. Try again later.") from error
        except APIConnectionError as error:
            raise LLMServiceError("LLM service is unavailable. Check the network and try again.") from error
        except APIError as error:
            raise LLMServiceError("LLM API returned an error. Check the model and configuration.") from error

    def _generate_with_ollama(self, customer_email, category, context):
        """Call Ollama's local chat API; no API key or cloud call is needed."""
        payload = json.dumps({
            "model": self.model, "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(customer_email["subject"], customer_email["email_body"], category, context)},
            ],
        }).encode("utf-8")
        request = Request(f"{self.base_url}/api/chat", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
            text = result.get("message", {}).get("content", "").strip()
            if not text:
                raise LLMServiceError("The local Ollama model returned an empty response.")
            return text
        except URLError as error:
            raise LLMServiceError("Ollama is unavailable. Start Ollama and confirm it is running on http://localhost:11434.") from error
        except TimeoutError as error:
            raise LLMServiceError("The local Ollama request timed out. Try again later.") from error
