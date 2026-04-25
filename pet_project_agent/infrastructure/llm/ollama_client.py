import json
import os

import requests


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or "llama3.2"

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
            },
        }

        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise RuntimeError(
                f"Ollama is unavailable at {self.base_url}. Ensure Ollama is running and the model `{self.model}` is pulled. Details: {error}"
            ) from error

        try:
            data = response.json()
        except json.JSONDecodeError as error:
            raise RuntimeError("Ollama returned invalid JSON.") from error

        generated_text = (data.get("response") or "").strip()

        if not generated_text:
            raise RuntimeError("Ollama returned an empty response.")

        return generated_text
