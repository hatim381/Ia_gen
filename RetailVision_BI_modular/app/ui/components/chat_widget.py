"""Chatbot analytique flottant (bas-droite), rendu sur toutes les pages.
Branche sur le service Q&A (Axe 3). Utilise un popover Streamlit positionne en CSS."""
from __future__ import annotations
import streamlit as st
from ui.services import get_qa_service


def _fmt_row(row: dict, group_by: str | None, metric: str) -> str:
    label = str(row.get(group_by, "—")) if group_by else ""
    val = row.get(metric)
    val_str = f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)
    return f"{label}: {val_str}" if label else val_str


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

        col_clear, _ = st.columns([1, 3])
        if col_clear.button("Effacer", key="chat_clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

        q = st.chat_input("Posez votre question…", key="chat_q")
        if q:
            last_user = next((m for r, m in reversed(st.session_state.chat_history) if r == "user"), None)
            if last_user != q:
                st.session_state.chat_history.append(("user", q))
                with st.spinner("Analyse en cours…"):
                    history = [{"role": r, "content": m} for r, m in st.session_state.chat_history[-6:]]
                    res = get_qa_service().answer(q, df, history)
                if res.ok:
                    ans = res.answer or "—"
                    if res.rows and res.spec:
                        apercu = ", ".join(
                            _fmt_row(r, res.spec.group_by, res.spec.metric)
                            for r in res.rows[:3]
                        )
                        ans += f"\n\n_{apercu}_"
                else:
                    ans = f"Erreur : {res.error or 'indisponible'}"
                st.session_state.chat_history.append(("assistant", ans))
            st.rerun()
