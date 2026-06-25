"""Facade Axe 2 — narration multi-pages."""
from __future__ import annotations
from core.domain.models import KPISet
from core.llm.client import LLMClient
from features.insights_narration.narrator import Narrator


class NarrationService:
    def __init__(self, llm: LLMClient | None = None):
        self.narrator = Narrator(llm)

    def generate(self, kpis) -> str:
        """Vue Globale : accepte KPISet ou dict (retro-compatible avec l'eval)."""
        data = kpis.as_dict() if isinstance(kpis, KPISet) else kpis
        return self.narrator.generate(data)

    def generate_for(self, title: str, facts: list[str]) -> str:
        """Autres pages : synthese a partir d'une liste de faits chiffres."""
        return self.narrator.generate_generic(title, facts)
