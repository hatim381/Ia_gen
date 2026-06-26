"""Orchestration UI Streamlit. Depend des facades features, jamais de leur interne."""
from __future__ import annotations
import streamlit as st

from core import config
from core.data import repository as repo
from ui import state as ui_state

st.set_page_config(page_title="RetailVision BI", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

_ICONS = {"Vue Globale": "🏠", "Performance": "📈", "Régions": "🗺️"}


def _inject_css():
    st.markdown("""<style>
/* === Sidebar === */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D0D1A 0%, #16162A 100%) !important;
    border-right: 1px solid rgba(79,139,249,0.12) !important;
}

/* === Primary buttons (page active / actions principales) === */
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #4F8BF9 0%, #3B6FE0 100%) !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(79,139,249,0.3) !important;
    font-weight: 700 !important;
    letter-spacing: 0.2px !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="baseButton-primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px rgba(79,139,249,0.5) !important;
}

/* === Secondary buttons === */
[data-testid="baseButton-secondary"] {
    border-color: rgba(255,255,255,0.1) !important;
    transition: border-color 0.15s ease, color 0.15s ease !important;
}
[data-testid="baseButton-secondary"]:hover {
    border-color: rgba(79,139,249,0.45) !important;
    color: #4F8BF9 !important;
}

/* === st.metric cards === */
[data-testid="stMetric"] {
    background: #1E1E2E !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    border-left: 4px solid #4F8BF9 !important;
}
[data-testid="stMetricValue"] { font-weight: 800 !important; }

/* === Popover (chatbot flottant) === */
[data-testid="stPopover"] > div > button {
    background: linear-gradient(135deg, #4F8BF9 0%, #7C3AED 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(79,139,249,0.4) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stPopover"] > div > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 28px rgba(79,139,249,0.6) !important;
}

/* === Alerts / Info / Warning / Success === */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* === DataFrames === */
[data-testid="stDataFrame"] { border-radius: 12px !important; overflow: hidden !important; }

/* === Expanders === */
[data-testid="stExpander"] {
    border: 1px solid rgba(79,139,249,0.15) !important;
    border-radius: 10px !important;
}

/* === Dividers === */
hr { border-color: rgba(255,255,255,0.06) !important; }

/* === Scrollbars === */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(79,139,249,0.25); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(79,139,249,0.5); }

/* === Text inputs === */
[data-testid="stTextInput"] > div > div {
    border-radius: 8px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stTextInput"] > div > div:focus-within {
    border-color: #4F8BF9 !important;
    box-shadow: 0 0 0 1px rgba(79,139,249,0.3) !important;
}

/* === Select boxes === */
[data-testid="stSelectbox"] > div > div { border-radius: 8px !important; }

/* === Captions === */
.stCaption { color: #9CA3AF !important; }

/* === Block container padding === */
.main .block-container { padding-top: 2rem !important; padding-bottom: 4rem !important; }
</style>""", unsafe_allow_html=True)


def _sidebar(df):
    from ui.components import voice_widget
    with st.sidebar:
        st.markdown("""<div style="padding:8px 0 16px 0">
<div style="display:flex;align-items:center;gap:12px">
  <span style="font-size:30px;line-height:1">📊</span>
  <div>
    <p style="font-size:17px;font-weight:800;margin:0;letter-spacing:-0.3px">RetailVision BI</p>
    <p style="font-size:10px;color:#6B7280;margin:0;text-transform:uppercase;letter-spacing:1px">Dashboard Analytics</p>
  </div>
</div></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#6B7280;font-weight:700;margin-bottom:10px">Navigation</p>', unsafe_allow_html=True)
        for page in config.PAGES:
            active = st.session_state.current_page == page
            if st.button(f"{_ICONS.get(page, '•')} {page}", key=f"nav_{page}",
                         use_container_width=True, type="primary" if active else "secondary"):
                st.session_state.current_page = page; st.rerun()

        st.markdown("---")
        st.markdown('<p style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#6B7280;font-weight:700;margin-bottom:10px">Filtres</p>', unsafe_allow_html=True)
        import pandas as pd
        mn, mx = df["date"].min().date(), df["date"].max().date()
        _v = st.session_state.get("date_filter_version", 0)
        dr = st.date_input("Période", value=(st.session_state.filter_date_start.date(),
                                             st.session_state.filter_date_end.date()),
                           min_value=mn, max_value=mx, key=f"sidebar_date_filter_{_v}")
        if isinstance(dr, (tuple, list)) and len(dr) == 2:
            st.session_state.filter_date_start = pd.Timestamp(dr[0])
            st.session_state.filter_date_end = pd.Timestamp(dr[1])

        _fv = st.session_state.get("filter_select_version", 0)
        ropts = ["Toutes"] + config.REGIONS
        ridx = 0 if not st.session_state.filter_region else ropts.index(st.session_state.filter_region)
        st.session_state.filter_region = (lambda v: None if v == "Toutes" else v)(
            st.selectbox("Région", ropts, index=ridx, key=f"sidebar_region_{_fv}")
        )

        copts = ["Toutes"] + config.CATEGORIES
        cidx = 0 if not st.session_state.filter_categorie else copts.index(st.session_state.filter_categorie)
        st.session_state.filter_categorie = (lambda v: None if v == "Toutes" else v)(
            st.selectbox("Catégorie", copts, index=cidx, key=f"sidebar_categorie_{_fv}")
        )

        if st.button("↺  Réinitialiser les filtres", use_container_width=True):
            from core.domain.state import Filters
            f = Filters.default()
            st.session_state.filter_date_start = f.date_start
            st.session_state.filter_date_end = f.date_end
            st.session_state.filter_region = st.session_state.filter_categorie = None
            st.session_state.date_filter_version = st.session_state.get("date_filter_version", 0) + 1
            new_fv = st.session_state.get("filter_select_version", 0) + 1
            st.session_state.filter_select_version = new_fv
            # Pré-initialise les nouvelles clés widgets pour forcer "Toutes" dès création
            st.session_state[f"sidebar_region_{new_fv}"] = "Toutes"
            st.session_state[f"sidebar_categorie_{new_fv}"] = "Toutes"
            st.rerun()

        st.markdown("---")
        voice_widget.render()

        st.markdown("---")
        st.markdown(
            f'<p style="font-size:10px;color:#4B5563;text-align:center;margin:0;line-height:1.6">'
            f'Modèle LLM : <b style="color:#6B7280">{config.OLLAMA_MODEL}</b><br>'
            f'RetailVision BI — EFREI M1 2026</p>',
            unsafe_allow_html=True,
        )


def main():
    _inject_css()
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
