"""Bloc reutilisable : genere une synthese LLM d'une page + bouton de lecture vocale (TTS)."""
from __future__ import annotations
import html
import streamlit as st

from ui.components import tts


@st.cache_resource
def _service():
    from features.insights_narration.service import NarrationService
    return NarrationService()


def render(title: str, facts: list[str], key: str):
    skey = f"narr_{key}"
    c1, c2, _ = st.columns([2, 1, 4])
    if c1.button("🤖 Générer la synthèse", key=f"gen_{key}", use_container_width=True):
        with st.spinner("Génération de la synthèse…"):
            try:
                st.session_state[skey] = _service().generate_for(title, facts)
            except Exception as exc:
                st.session_state[skey] = ""
                st.warning(f"Erreur narration : {exc}. Vérifiez qu'Ollama tourne et que le "
                           "modèle est téléchargé (ollama pull gemma3:4b).")
    text = st.session_state.get(skey, "")
    if text:
        with c2:
            tts.read_button(text, key=f"read_{key}")
        st.markdown(
            f"""<div style="background:#1E1E2E;border-radius:12px;padding:14px 20px;border-left:4px solid #4F8BF9;margin:6px 0 14px">
<p style="margin:0;line-height:1.6">{html.escape(text)}</p></div>""",
            unsafe_allow_html=True,
        )
