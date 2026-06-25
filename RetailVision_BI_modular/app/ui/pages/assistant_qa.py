"""Page Axe 3 — Assistant Q&A analytique (text-to-query securise)."""
from __future__ import annotations
import pandas as pd
import streamlit as st


@st.cache_resource
def _qa_service():
    from features.analytics_qa.service import AnalyticsQAService
    return AnalyticsQAService()


def render(df: pd.DataFrame):
    st.title("💬 Assistant analytique")
    st.caption("Posez une question en langage naturel sur les ventes (ex : « Quelle région a le plus de CA en 2025 ? »).")

    question = st.text_input("Votre question", key="qa_question",
                             placeholder="Top 3 des régions par CA en 2025")
    if st.button("Interroger", use_container_width=False) and question.strip():
        with st.spinner("Analyse…"):
            st.session_state.qa_result = _qa_service().answer(question, df)

    res = st.session_state.get("qa_result")
    if res is None:
        return
    if not res.ok:
        st.warning(res.error); return

    st.success(res.answer)
    if res.spec:
        s = res.spec
        st.caption(f"Requête interprétée : {s.agg} {s.metric}"
                   + (f" par {s.group_by}" if s.group_by else "")
                   + (f" · {s.region}" if s.region else "") + (f" · {s.categorie}" if s.categorie else "")
                   + (f" · {s.year}" if s.year else ""))
    if res.rows:
        st.dataframe(pd.DataFrame(res.rows), hide_index=True, use_container_width=True)
