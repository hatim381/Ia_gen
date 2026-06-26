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
        </style>""",
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("chat_history", [])

    n_msgs = len(st.session_state.chat_history)
    btn_label = f"💬 Assistant ({n_msgs // 2})" if n_msgs >= 2 else "💬 Assistant"

    with st.popover(btn_label, use_container_width=False):
        st.markdown(
            """<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
<span style="font-size:20px">🤖</span>
<div><p style="font-weight:700;margin:0;font-size:15px">Assistant analytique</p>
<p style="color:#9CA3AF;font-size:11px;margin:0">Posez une question sur les ventes</p></div></div>""",
            unsafe_allow_html=True,
        )
        st.divider()

        for role, msg in st.session_state.chat_history[-8:]:
            with st.chat_message(role):
                st.markdown(msg)

        # st.chat_input ne se soumet pas de maniere fiable a l'interieur d'un popover
        # (le rerun referme le popover avant le traitement) -> on utilise un form.
        with st.form("chat_form", clear_on_submit=True):
            q = st.text_input("Question", placeholder="Ex : Quel est le CA du Nord en 2025 ?",
                              label_visibility="collapsed", key="chat_q")
            col_send, col_clear = st.columns([3, 1])
            submitted = col_send.form_submit_button("Envoyer ↑", use_container_width=True, type="primary")
            if col_clear.form_submit_button("✕", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        if submitted and q and q.strip():
            st.session_state.chat_history.append(("user", q))
            with st.spinner("Analyse en cours…"):
                history = [{"role": r, "content": m} for r, m in st.session_state.chat_history[-6:]]
                res = get_qa_service().answer(q, df, history)
            if res.ok:
                ans = res.answer or "—"
                # Apercu seulement pour les résultats groupés (scalaires déjà formatés dans answer)
                if res.rows and res.spec and res.spec.group_by:
                    apercu = ", ".join(
                        _fmt_row(r, res.spec.group_by, res.spec.metric)
                        for r in res.rows[:3]
                    )
                    ans += f"\n\n_{apercu}_"
            else:
                ans = f"Erreur : {res.error or 'indisponible'}"
            st.session_state.chat_history.append(("assistant", ans))
            st.rerun()
