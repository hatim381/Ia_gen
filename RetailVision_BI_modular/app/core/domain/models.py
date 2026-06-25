"""Modeles de domaine partages — dataclasses pures, sans dependance UI/LLM."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Intent:
    action: str = "unknown"              # navigate|filter|reset|narrate|help|clear_filter|query|unknown
    target_page: str | None = None
    parameters: dict = field(default_factory=dict)
    pipeline: str = "fast_track"         # fast_track|fuzzy|llm|llm_unavailable|llm_error


@dataclass
class KPISet:
    ca_2025: float = 0.0
    ca_delta_pct: float = 0.0
    tx_delta_pct: float = 0.0
    marge_2025: float = 0.0
    marge_delta_pts: float = 0.0
    panier_delta_pct: float = 0.0
    top_region: str = ""
    top_categorie: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class QuerySpec:
    metric: str = "ca"
    agg: str = "sum"
    group_by: str | None = None
    region: str | None = None
    categorie: str | None = None
    year: int | None = None
    date_start: str | None = None   # YYYY-MM-DD, prioritaire sur year si fourni
    date_end: str | None = None     # YYYY-MM-DD
    sort: str = "desc"
    limit: int | None = None
    valid: bool = True


@dataclass
class QueryResult:
    ok: bool
    spec: QuerySpec | None = None
    rows: list[dict] = field(default_factory=list)
    answer: str = ""
    error: str = ""


@dataclass
class Effect:
    """Effet a appliquer sur l'etat par la couche UI (decouple les features de Streamlit)."""
    type: str                            # set_page|set_filter|reset|narrate|message
    payload: dict = field(default_factory=dict)
