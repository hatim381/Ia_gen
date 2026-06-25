"""Client LLM UNIQUE (Ollama local). Tous les axes passent par ici : un seul point
de configuration (modele, timeout, format JSON, gestion d'erreur)."""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass

from core import config

log = logging.getLogger("llm")


@dataclass
class LLMResult:
    ok: bool
    text: str = ""
    data: dict | None = None
    error: str = ""


class LLMClient:
    def __init__(self, model: str | None = None, timeout: int | None = None):
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout or config.OLLAMA_TIMEOUT

    def _client(self):
        import ollama
        return ollama.Client(timeout=self.timeout)

    def chat_json(self, prompt: str, num_predict: int = 200) -> LLMResult:
        """Retourne un JSON parse (format=json + grammar sampling)."""
        try:
            resp = self._client().chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0, "num_predict": num_predict},
                format="json",
            )
            raw = resp["message"]["content"].strip()
            return LLMResult(ok=True, text=raw, data=json.loads(raw))
        except ImportError:
            return LLMResult(ok=False, error="ollama_unavailable")
        except Exception as exc:  # timeout, modele absent, JSON invalide
            log.warning("LLM chat_json error: %s", exc)
            return LLMResult(ok=False, error=str(exc))

    def chat_text(self, prompt: str, temperature: float = 0.4, num_predict: int = 300) -> LLMResult:
        try:
            resp = self._client().chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_predict": num_predict},
            )
            return LLMResult(ok=True, text=resp["message"]["content"].strip())
        except ImportError:
            return LLMResult(ok=False, error="ollama_unavailable")
        except Exception as exc:
            log.warning("LLM chat_text error: %s", exc)
            return LLMResult(ok=False, error=str(exc))
