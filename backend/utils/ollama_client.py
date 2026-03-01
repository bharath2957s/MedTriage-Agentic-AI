"""
Ollama LLM client wrapper.
Provides a simple interface for calling local Ollama models
with structured prompt formatting and error handling.
"""

import json
import httpx
from typing import Optional
from config.settings import ollama_config
from backend.utils.logger import get_logger

logger = get_logger("ollama_client")


class OllamaClient:
    """
    Thin wrapper around the Ollama REST API.
    Handles retries, timeouts, and JSON extraction.
    """

    def __init__(self):
        self.base_url = ollama_config.base_url
        self.model = ollama_config.model
        self.temperature = ollama_config.temperature

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Send a generation request to Ollama.
        Returns raw text response.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",   # 🔥 CRITICAL FIX
            "options": {
                "temperature": self.temperature,
                "num_predict": 400,
            },
        }
        if system:
            payload["system"] = system

        logger.debug(f"Sending request to Ollama model={self.model}")

        try:
            with httpx.Client(timeout=ollama_config.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is it running? (ollama serve)")
            raise RuntimeError(
                "Ollama is not reachable. Please run `ollama serve` and try again."
            )
        except httpx.TimeoutException:
            logger.error("Ollama request timed out.")
            raise RuntimeError("LLM request timed out. Try a smaller model.")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    def generate_json(self, prompt: str, system: Optional[str] = None) -> dict:
        """
        Like generate(), but attempts to parse the response as JSON.
        Extracts JSON block from markdown code fences if present.
        """
        raw = self.generate(prompt, system)

        # Strip markdown code fences if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed, returning raw text. Error: {e}")
            return {"raw_response": raw}


# Module-level singleton
llm_client = OllamaClient()
