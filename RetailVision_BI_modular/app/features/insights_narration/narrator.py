"""Axe 2 — Generation de syntheses executives (LLM via core). Pur (pas de Streamlit)."""
from __future__ import annotations
from core.llm.client import LLMClient
from core.llm import prompts


class Narrator:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def generate(self, kpis: dict) -> str:
        """Synthese Vue Globale (KPIs YoY)."""
        res = self.llm.chat_text(prompts.narration(kpis), temperature=0.4)
        if not res.ok:
            raise RuntimeError(res.error or "narration indisponible")
        return res.text

    def generate_generic(self, title: str, facts: list[str]) -> str:
        """Synthese d'une page quelconque a partir de faits chiffres."""
        res = self.llm.chat_text(prompts.narration_generic(title, facts), temperature=0.4)
        if not res.ok:
            raise RuntimeError(res.error or "narration indisponible")
        return res.text
