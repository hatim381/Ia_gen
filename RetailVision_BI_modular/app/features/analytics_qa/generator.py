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

    def generate(self, question: str, history: list[dict] | None = None) -> QuerySpec | None:
        res = self.llm.chat_json(prompts.query_spec(question, history), num_predict=200)
        if not res.ok:
            return None
        d = res.data or {}
        if d.get("valid") is False:
            return QuerySpec(valid=False)
        raw_region = d.get("region")
        raw_categorie = d.get("categorie")
        region = _scalar_or_none(raw_region, config.REGIONS)
        categorie = _scalar_or_none(raw_categorie, config.CATEGORIES)
        # Entite mentionnee mais absente de la liste -> requete hors perimetre
        if raw_region and raw_region not in (None, "null") and region is None:
            return QuerySpec(valid=False)
        if raw_categorie and raw_categorie not in (None, "null") and categorie is None:
            return QuerySpec(valid=False)
        year = d.get("year") if d.get("year") in (2024, 2025) else None
        date_start = _date_or_none(d.get("date_start"))
        date_end = _date_or_none(d.get("date_end"))
        # Aucune période précisée → défaut 2025
        if year is None and date_start is None and date_end is None:
            year = 2025
        return QuerySpec(
            metric=d.get("metric", "ca"), agg=d.get("agg", "sum"),
            group_by=d.get("group_by") or None,
            region=region,
            categorie=categorie,
            year=year,
            date_start=date_start,
            date_end=date_end,
            sort=d.get("sort", "desc"), limit=d.get("limit"), valid=True,
        )
