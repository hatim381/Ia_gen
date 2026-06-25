"""Client LLM UNIQUE (Ollama local). Tous les axes passent par ici : un seul point
de configuration (modele, timeout, format JSON, gestion d'erreur)."""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core import config

log = logging.getLogger("llm")


def _log_call(model: str, method: str, prompt: str, result: "LLMResult", elapsed: float) -> None:
    log_path = Path(config.LLM_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "model": model,
        "method": method,
        "latency_ms": round(elapsed * 1000, 1),
        "ok": result.ok,
        "prompt": prompt,
        "response": result.text,
        "error": result.error,
    }
    try:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        log.warning("LLM log write error: %s", exc)


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
        t0 = time.perf_counter()
        try:
            resp = self._client().chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0, "num_predict": num_predict},
                format="json",
            )
            raw = resp["message"]["content"].strip()
            result = LLMResult(ok=True, text=raw, data=json.loads(raw))
        except ImportError:
            result = LLMResult(ok=False, error="ollama_unavailable")
        except Exception as exc:
            log.warning("LLM chat_json error: %s", exc)
            result = LLMResult(ok=False, error=str(exc))
        _log_call(self.model, "chat_json", prompt, result, time.perf_counter() - t0)
        return result

    def chat_text(self, prompt: str, temperature: float = 0.4, num_predict: int = 300) -> LLMResult:
        t0 = time.perf_counter()
        try:
            resp = self._client().chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_predict": num_predict},
            )
            result = LLMResult(ok=True, text=resp["message"]["content"].strip())
        except ImportError:
            result = LLMResult(ok=False, error="ollama_unavailable")
        except Exception as exc:
            log.warning("LLM chat_text error: %s", exc)
            result = LLMResult(ok=False, error=str(exc))
        _log_call(self.model, "chat_text", prompt, result, time.perf_counter() - t0)
        return result
