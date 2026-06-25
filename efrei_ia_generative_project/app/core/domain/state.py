"""Abstraction de l'etat applicatif. Les features manipulent AppState (pur) ;
la couche UI synchronise AppState <-> st.session_state. Aucun import Streamlit ici."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

from core import config


@dataclass
class Filters:
    date_start: pd.Timestamp = None
    date_end: pd.Timestamp = None
    region: str | None = None
    categorie: str | None = None

    @classmethod
    def default(cls) -> "Filters":
        return cls(pd.Timestamp(config.DATE_MIN), pd.Timestamp(config.DATE_MAX), None, None)


@dataclass
class AppState:
    current_page: str = "Vue Globale"
    filters: Filters = None
    message: str = ""
    narrate_requested: bool = False

    @classmethod
    def default(cls) -> "AppState":
        return cls(current_page="Vue Globale", filters=Filters.default())
