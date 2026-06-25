"""Page Axe 3 — Assistant Q&A analytique (text-to-query securise)."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from ui.services import get_qa_service


def render(df: pd.DataFrame):
    st.title("💬 Assistant analytique")
    st.caption("Posez une question en langage naturel sur les ventes (ex : « Quelle région a le plus de CA en 2025 ? »).")

    st.session_state.setdefault("qa_history", [])

    for entry in st.session_state.qa_history:
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])

    question = st.chat_input("Posez votre question…", key="qa_chat_input")
    if question:
        st.session_state.qa_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        history_ctx = st.session_state.qa_history[-6:]
        with st.spinner("Analyse…"):
            res = get_qa_service().answer(question, df, history_ctx)

        if not res.ok:
            reply = f"Erreur : {res.error or 'indisponible'}"
        else:
            reply = res.answer or "—"

        st.session_state.qa_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

        if res.ok and res.spec:
            s = res.spec
            st.caption(
                f"Requête : {s.agg} {s.metric}"
                + (f" par {s.group_by}" if s.group_by else "")
                + (f" · {s.region}" if s.region else "")
                + (f" · {s.categorie}" if s.categorie else "")
                + (f" · {s.year}" if s.year else "")
            )
        if res.ok and res.rows:
            st.dataframe(pd.DataFrame(res.rows), hide_index=True, use_container_width=True)

    if st.session_state.qa_history and st.button("Effacer la conversation", key="qa_clear"):
        st.session_state.qa_history = []
        st.rerun()
