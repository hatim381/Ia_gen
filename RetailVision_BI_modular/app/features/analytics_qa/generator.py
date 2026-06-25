"""Axe 3 — Traduction question -> QuerySpec via LLM (sortie JSON validee)."""
from __future__ import annotations
from core import config
from core.domain.models import QuerySpec
from core.llm.client import LLMClient
from core.llm import prompts


def _scalar_or_none(value, valid_list: list) -> str | None:
    """Normalise la valeur retournee par le LLM : liste ou string 'null' -> None."""
    if not value or value == "null":
        return None
    if isinstance(value, list):
        return None
    return value if value in valid_list else None


def _date_or_none(value) -> str | None:
    """Valide et normalise une date YYYY-MM-DD retournee par le LLM."""
    if not value or value in ("null", "None"):
        return None
    try:
        import pandas as pd
        return str(pd.Timestamp(value).date())
    except Exception:
        return None


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
            group_by=d.get("group_by") or None,
            region=_scalar_or_none(d.get("region"), config.REGIONS),
            categorie=_scalar_or_none(d.get("categorie"), config.CATEGORIES),
            year=d.get("year") if d.get("year") in (2024, 2025) else None,
            date_start=_date_or_none(d.get("date_start")),
            date_end=_date_or_none(d.get("date_end")),
            sort=d.get("sort", "desc"), limit=d.get("limit"), valid=True,
        )
