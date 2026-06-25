"""Axe 3 — Traduction question -> QuerySpec via LLM (sortie JSON validee)."""
from __future__ import annotations
from core.domain.models import QuerySpec
from core.llm.client import LLMClient
from core.llm import prompts


class QuerySpecGenerator:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def generate(self, question: str) -> QuerySpec | None:
        res = self.llm.chat_json(prompts.query_spec(question), num_predict=200)
        if not res.ok:
            return None
        d = res.data or {}
        if d.get("valid") is False:
            return QuerySpec(valid=False)
        return QuerySpec(
            metric=d.get("metric", "ca"), agg=d.get("agg", "sum"),
            group_by=d.get("group_by") or None, region=d.get("region") or None,
            categorie=d.get("categorie") or None,
            year=d.get("year") if d.get("year") in (2024, 2025) else None,
            sort=d.get("sort", "desc"), limit=d.get("limit"), valid=True,
        )
