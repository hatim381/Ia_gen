"""Axe 2 — Generation de la synthese executive a partir des KPIs (LLM via core)."""
from __future__ import annotations
from core.llm.client import LLMClient
from core.llm import prompts


class Narrator:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def generate(self, kpis: dict) -> str:
        res = self.llm.chat_text(prompts.narration(kpis), temperature=0.4)
        if not res.ok:
            raise RuntimeError(res.error or "narration indisponible")
        return res.text
