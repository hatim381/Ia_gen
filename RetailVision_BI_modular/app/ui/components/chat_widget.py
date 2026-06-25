"""Chatbot analytique flottant (bas-droite), rendu sur toutes les pages.
Branche sur le service Q&A (Axe 3). Utilise un popover Streamlit positionne en CSS."""
from __future__ import annotations
import streamlit as st


@st.cache_resource
def _qa_service():
    from features.analytics_qa.service import AnalyticsQAService
    return AnalyticsQAService()


def render(df):
    # Ancre le popover en bas a droite de la fenetre.
    st.markdown(
        """<style>
        div[data-testid="stPopover"] { position: fixed; bottom: 22px; right: 22px; z-index: 1000; }
        div[data-testid="stPopover"] button { border-radius: 999px; box-shadow: 0 4px 14px rgba(0,0,0,.35); }
        </style>""",
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("chat_history", [])

    with st.popover("💬 Assistant", use_container_width=False):
        st.markdown("**Assistant analytique** — posez une question sur les ventes.")
        for role, msg in st.session_state.chat_history[-8:]:
            with st.chat_message(role):
                st.markdown(msg)

        q = st.text_input("Votre question", key="chat_q",
                          placeholder="Ex : top 3 des régions par CA en 2025",
                          label_visibility="collapsed")
        c1, c2 = st.columns([1, 1])
        if c1.button("Envoyer", key="chat_send", use_container_width=True) and q.strip():
            # Dédoublonnage : évite d'ajouter la même question si le bouton est recliqué
            last_user = next((m for r, m in reversed(st.session_state.chat_history) if r == "user"), None)
            if last_user != q:
                st.session_state.chat_history.append(("user", q))
                with st.spinner("Analyse en cours…"):
                    res = _qa_service().answer(q, df)
                if res.ok:
                    ans = res.answer or "—"
                    if res.rows:
                        apercu = ", ".join(
                            f"{list(r.values())[0]}: {list(r.values())[-1]:,.0f}"
                            if isinstance(list(r.values())[-1], (int, float)) else str(r)
                            for r in res.rows[:3])
                        ans += f"\n\n_{apercu}_"
                else:
                    ans = f"Erreur : {res.error or 'indisponible'}"
                st.session_state.chat_history.append(("assistant", ans))
            st.session_state.chat_q = ""
            st.rerun()
        if c2.button("Effacer", key="chat_clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
