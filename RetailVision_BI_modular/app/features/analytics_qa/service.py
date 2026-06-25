"""Facade Axe 3 : question langage naturel -> QueryResult (spec sure + execution)."""
from __future__ import annotations
import pandas as pd

from core.domain.models import QueryResult
from core.llm.client import LLMClient
from core.llm import prompts
from features.analytics_qa.generator import QuerySpecGenerator
from features.analytics_qa import query_engine


class AnalyticsQAService:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()
        self.generator = QuerySpecGenerator(self.llm)

    def answer(self, question: str, df: pd.DataFrame, history: list[dict] | None = None) -> QueryResult:
        spec = self.generator.generate(question, history)
        if spec is None:
            return QueryResult(ok=False, error="Assistant indisponible (LLM non joignable).")
        if not spec.valid:
            return QueryResult(ok=False, spec=spec, error="Question hors périmètre du dashboard.")
        result = query_engine.execute(spec, df)
        if result.ok and result.rows:
            result.answer = self._narrate(question, result)
        return result

    def _narrate(self, question: str, result: QueryResult) -> str:
        spec = result.spec
        spec_desc = (
            f"{spec.agg} de {spec.metric}"
            + (f" par {spec.group_by}" if spec.group_by else "")
            + (f" pour {spec.region}" if spec.region else "")
            + (f" · {spec.categorie}" if spec.categorie else "")
            + (f" · {spec.year}" if spec.year else "")
        )
        llm_res = self.llm.chat_text(
            prompts.qa_narration(question, result.rows, spec_desc),
            temperature=0.3,
            num_predict=150,
        )
        return llm_res.text if llm_res.ok and llm_res.text else result.answer
