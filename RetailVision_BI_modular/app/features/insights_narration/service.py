"""Facade Axe 2."""
from __future__ import annotations
from core.domain.models import KPISet
from core.llm.client import LLMClient
from features.insights_narration.narrator import Narrator


class NarrationService:
    def __init__(self, llm: LLMClient | None = None):
        self.narrator = Narrator(llm)

    def generate(self, kpis) -> str:
        data = kpis.as_dict() if isinstance(kpis, KPISet) else kpis
        return self.narrator.generate(data)
