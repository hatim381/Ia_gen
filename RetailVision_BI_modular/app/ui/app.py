"""Orchestration UI Streamlit. Depend des facades features, jamais de leur interne."""
from __future__ import annotations
import streamlit as st

from core import config
from core.data import repository as repo
from ui import state as ui_state

st.set_page_config(page_title="RetailVision BI", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

_ICONS = {"Vue Globale": "🏠", "Performance": "📈", "Régions": "🗺️"}


def _sidebar(df):
    from ui.components import voice_widget
    with st.sidebar:
        st.title("📊 RetailVision BI")
        st.markdown("---"); st.subheader("Navigation")
        for page in config.PAGES:
            active = st.session_state.current_page == page
            if st.button(f"{_ICONS.get(page, '•')} {page}", key=f"nav_{page}",
                         use_container_width=True, type="primary" if active else "secondary"):
                st.session_state.current_page = page; st.rerun()

        st.markdown("---"); st.subheader("Filtres")
        import pandas as pd
        mn, mx = df["date"].min().date(), df["date"].max().date()
        dr = st.date_input("Période", value=(st.session_state.filter_date_start.date(),
                                             st.session_state.filter_date_end.date()),
                           min_value=mn, max_value=mx)
        if len(dr) == 2:
            st.session_state.filter_date_start = pd.Timestamp(dr[0])
            st.session_state.filter_date_end = pd.Timestamp(dr[1])

        ropts = ["Toutes"] + config.REGIONS
        ridx = 0 if not st.session_state.filter_region else ropts.index(st.session_state.filter_region)
        st.session_state.filter_region = (lambda v: None if v == "Toutes" else v)(st.selectbox("Région", ropts, index=ridx))

        copts = ["Toutes"] + config.CATEGORIES
        cidx = 0 if not st.session_state.filter_categorie else copts.index(st.session_state.filter_categorie)
        st.session_state.filter_categorie = (lambda v: None if v == "Toutes" else v)(st.selectbox("Catégorie", copts, index=cidx))

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
    if page == "Performance":
        from ui.pages.performance import render; render(df, df_filtered)
    elif page == "Régions":
        from ui.pages.regions import render; render(df, df_filtered)
    else:
        from ui.pages.vue_globale import render; render(df, df_filtered)

    # Chatbot flottant present sur TOUTES les pages
    from ui.components import chat_widget
    chat_widget.render(df)


if __name__ == "__main__":
    main()
