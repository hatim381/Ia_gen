"""Facade Axe 3 : question langage naturel -> QueryResult (spec sure + execution)."""
from __future__ import annotations
import pandas as pd

from core.domain.models import QueryResult
from core.llm.client import LLMClient
from features.analytics_qa.generator import QuerySpecGenerator
from features.analytics_qa import query_engine


class AnalyticsQAService:
    def __init__(self, llm: LLMClient | None = None):
        self.generator = QuerySpecGenerator(llm)

    def answer(self, question: str, df: pd.DataFrame) -> QueryResult:
        spec = self.generator.generate(question)
        if spec is None:
            return QueryResult(ok=False, error="Assistant indisponible (LLM non joignable).")
        if not spec.valid:
            return QueryResult(ok=False, spec=spec, error="Question hors périmètre du dashboard.")
        return query_engine.execute(spec, df)
