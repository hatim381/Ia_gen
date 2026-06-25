"""Composant UI de commande vocale : bouton classique + ecoute par mot-cle (openWakeWord)."""
from __future__ import annotations
import queue as _queue
import streamlit as st

from core import config
from ui import state as ui_state


@st.cache_resource
def _listener():
    from core.stt.microphone import MicListener
    return MicListener()


@st.cache_resource
def _voice_service():
    from features.voice_navigation.service import VoiceNavigationService
    return VoiceNavigationService()


def _commands_help():
    with st.expander("Commandes disponibles", expanded=False):
        st.markdown(
            "**Navigation** : *Accueil*, *Performance*, *Régions*, *Reset*, *Résumé*\n\n"
            "**Filtres** : *Région Nord*, *Catégorie Sport*, *Ventes de janvier 2025*"
        )


def render():
    st.subheader("🎤 Commande vocale")
    try:
        from streamlit_autorefresh import st_autorefresh
    except ImportError:
        st.info("Dépendance manquante : streamlit-autorefresh")
        return

    try:
        listener = _listener()
    except Exception as exc:
        st.info(f"Commande vocale indisponible : {exc}")
        _commands_help()
        return
    svc = _voice_service()

    if listener.error:
        st.error(f"Erreur micro : {listener.error}")

    if listener.is_running:
        if listener.armed:
            st.caption("🔴 Écoute active — dites votre commande")
        else:
            st.caption(f"🟡 En veille — dites « {config.WAKE_PHRASE_LABEL} » pour activer")
        if st.button("⏹ Arrêter", use_container_width=True):
            listener.stop(); st.rerun()
        st_autorefresh(interval=500, key="mic_autorefresh")

        # Evenement mot-cle detecte
        try:
            if listener.status_queue.get_nowait() == "wake":
                st.session_state.stt_message = "🔔 Mot-clé détecté — écoute activée."
                st.rerun()
        except _queue.Empty:
            pass
        # Commande transcrite
        try:
            transcript = listener.transcript_queue.get_nowait()
            st.session_state.stt_transcript = transcript
            state = ui_state.load()
            state, message, _ = svc.handle(transcript, state)
            ui_state.save(state)
            st.session_state.stt_message = message
            st.rerun()
        except _queue.Empty:
            pass
    else:
        if st.button("🎤 Démarrer l'écoute", use_container_width=True):
            listener.start(armed=True); st.rerun()
        if listener.wake_available:
            if st.button(f"🪄 Écoute mains-libres (« {config.WAKE_PHRASE_LABEL} »)", use_container_width=True):
                listener.start(armed=False); st.rerun()
        else:
            st.caption("Mode mains-libres indisponible (openWakeWord non installé).")

    if st.session_state.stt_transcript:
        st.caption(f"Transcription : *{st.session_state.stt_transcript}*")
    if st.session_state.stt_message:
        msg = st.session_state.stt_message
        (st.warning if "non reconnue" in msg.lower() else st.success)(msg)
    _commands_help()
