"""Orchestration UI Streamlit. Depend des facades features, jamais de leur interne."""
from __future__ import annotations
import streamlit as st

from core import config
from core.data import repository as repo
from ui import state as ui_state

st.set_page_config(page_title="RetailVision BI", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

_ICONS = {"Vue Globale": "🏠", "Performance": "📈", "Régions": "🗺️", "Assistant Q&A": "💬"}


def _sidebar(df):
    from ui.components import voice_widget
    with st.sidebar:
        st.title("📊 RetailVision BI")
        st.markdown("---"); st.subheader("Navigation")
        for page in config.PAGES:
            active = st.session_state.current_page == page
            if st.button(f"{_ICONS[page]} {page}", key=f"nav_{page}",
                         use_container_width=True, type="primary" if active else "secondary"):
                st.session_state.current_page = page; st.rerun()

        st.markdown("---"); st.subheader("Filtres")
        mn, mx = df["date"].min().date(), df["date"].max().date()
        dr = st.date_input("Période", value=(st.session_state.filter_date_start.date(),
                                             st.session_state.filter_date_end.date()),
                           min_value=mn, max_value=mx)
        if len(dr) == 2:
            import pandas as pd
            st.session_state.filter_date_start = pd.Timestamp(dr[0])
            st.session_state.filter_date_end = pd.Timestamp(dr[1])

        ropts = ["Toutes"] + config.REGIONS
        ridx = 0 if not st.session_state.filter_region else ropts.index(st.session_state.filter_region)
        rsel = st.selectbox("Région", ropts, index=ridx)
        st.session_state.filter_region = None if rsel == "Toutes" else rsel

        copts = ["Toutes"] + config.CATEGORIES
        cidx = 0 if not st.session_state.filter_categorie else copts.index(st.session_state.filter_categorie)
        csel = st.selectbox("Catégorie", copts, index=cidx)
        st.session_state.filter_categorie = None if csel == "Toutes" else csel

        if st.button("🔄 Réinitialiser les filtres", use_container_width=True):
            from core.domain.state import Filters
            f = Filters.default()
            st.session_state.filter_date_start, st.session_state.filter_date_end = f.date_start, f.date_end
            st.session_state.filter_region = st.session_state.filter_categorie = None
            st.rerun()

        st.markdown("---")
        voice_widget.render()


def main():
    ui_state.init()
    df = repo.load_sales()
    _sidebar(df)
    state = ui_state.load()
    df_filtered = repo.apply_filters(df, state.filters)

    page = state.current_page
    if page == "Vue Globale":
        from ui.pages.vue_globale import render; render(df, df_filtered)
    elif page == "Performance":
        from ui.pages.performance import render; render(df, df_filtered)
    elif page == "Régions":
        from ui.pages.regions import render; render(df, df_filtered)
    elif page == "Assistant Q&A":
        from ui.pages.assistant_qa import render; render(df)


if __name__ == "__main__":
    main()
