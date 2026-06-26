"""Adaptateur d'etat : synchronise st.session_state <-> AppState (core).
C'est la SEULE couche qui connait a la fois Streamlit et le domaine."""
from __future__ import annotations
import pandas as pd
import streamlit as st

from core import config
from core.domain.state import AppState, Filters


def init():
    defaults = {
        "current_page": "Vue Globale",
        "filter_date_start": pd.Timestamp(config.DATE_MIN),
        "filter_date_end": pd.Timestamp(config.DATE_MAX),
        "filter_region": None, "filter_categorie": None,
        "stt_transcript": "", "stt_message": "",
        "narrate_requested": False, "narrative_text": "", "qa_result": None,
        "date_filter_version": 0,  # incremente au reset pour forcer la recreation du widget date
        "filter_select_version": 0,  # idem pour les selectbox region/categorie
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def load() -> AppState:
    return AppState(
        current_page=st.session_state.current_page,
        filters=Filters(st.session_state.filter_date_start, st.session_state.filter_date_end,
                        st.session_state.filter_region, st.session_state.filter_categorie),
        narrate_requested=st.session_state.narrate_requested,
    )


def save(state: AppState):
    st.session_state.current_page = state.current_page
    f = state.filters
    st.session_state.filter_date_start = f.date_start
    st.session_state.filter_date_end = f.date_end
    st.session_state.filter_region = f.region
    st.session_state.filter_categorie = f.categorie
    st.session_state.narrate_requested = state.narrate_requested
