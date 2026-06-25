"""Axe 3 — Execution SURE d'une QuerySpec sur le dataframe. Aucun eval/exec :
seuls des champs whitelistes et des operations pandas controlees sont autorises."""
from __future__ import annotations
import pandas as pd

from core import config
from core.domain.models import QuerySpec, QueryResult

METRICS = {"ca", "transactions", "marge_pct"}
AGGS = {"sum": "sum", "mean": "mean", "max": "max", "min": "min"}
GROUPS = {"region": "region", "categorie": "categorie", "mois": "mois"}


def validate(spec: QuerySpec) -> str | None:
    if spec.metric not in METRICS:
        return f"métrique non autorisée : {spec.metric}"
    if spec.agg not in AGGS:
        return f"agrégation non autorisée : {spec.agg}"
    if spec.group_by not in (None, *GROUPS):
        return f"group_by non autorisé : {spec.group_by}"
    if spec.region not in (None, *config.REGIONS):
        return f"région inconnue : {spec.region}"
    if spec.categorie not in (None, *config.CATEGORIES):
        return f"catégorie inconnue : {spec.categorie}"
    if spec.year not in (None, 2024, 2025):
        return f"année hors périmètre : {spec.year}"
    return None


def execute(spec: QuerySpec, df: pd.DataFrame) -> QueryResult:
    err = validate(spec)
    if err:
        return QueryResult(ok=False, spec=spec, error=err)
    d = df
    if spec.year:
        d = d[d["date"].dt.year == spec.year]
    if spec.region:
        d = d[d["region"] == spec.region]
    if spec.categorie:
        d = d[d["categorie"] == spec.categorie]
    if d.empty:
        return QueryResult(ok=True, spec=spec, rows=[], answer="Aucune donnée pour ces critères.")

    if spec.group_by:
        if spec.group_by == "mois":
            d = d.assign(mois=d["date"].dt.to_period("M").dt.to_timestamp())
            grouped = d.groupby("mois")[spec.metric].agg(AGGS[spec.agg]).reset_index()
        else:
            grouped = d.groupby(spec.group_by)[spec.metric].agg(AGGS[spec.agg]).reset_index()
        grouped = grouped.sort_values(spec.metric, ascending=(spec.sort == "asc"))
        if spec.limit:
            grouped = grouped.head(int(spec.limit))
        rows = grouped.to_dict("records")
        answer = _phrase(spec, rows)
    else:
        val = getattr(d[spec.metric], AGGS[spec.agg])()
        rows = [{spec.metric: float(val)}]
        answer = f"{spec.agg} {spec.metric} = {float(val):,.2f}"
    return QueryResult(ok=True, spec=spec, rows=rows, answer=answer)


def _phrase(spec: QuerySpec, rows: list[dict]) -> str:
    if not rows:
        return "Aucun résultat."
    top = rows[0]
    key = spec.group_by
    v = top.get(spec.metric, 0)
    disp = f"{v*100:.1f}%" if spec.metric == "marge_pct" else f"{v:,.0f}"
    return f"En tête ({spec.agg} {spec.metric}) : {top.get(key)} avec {disp}." if key else f"Résultat : {disp}"
