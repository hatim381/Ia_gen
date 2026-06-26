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
    st.markdown(
        '<p style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#9CA3AF;margin-bottom:10px">🎤 Commande vocale</p>',
        unsafe_allow_html=True,
    )
    try:
        from streamlit_autorefresh import st_autorefresh
    except ImportError:
        st.info("Dépendance manquante : streamlit-autorefresh", icon="ℹ️")
        return

    try:
        listener = _listener()
    except Exception as exc:
        st.info(f"Commande vocale indisponible : {exc}", icon="🎙️")
        _commands_help()
        return
    svc = _voice_service()

    if listener.error:
        st.error(f"Erreur micro : {listener.error}", icon="🚫")

    if listener.is_running:
        if listener.armed:
            st.markdown(
                '<div style="background:rgba(231,76,60,0.12);border:1px solid rgba(231,76,60,0.3);border-radius:8px;padding:8px 12px;margin-bottom:8px">'
                '<span style="color:#E74C3C;font-size:12px;font-weight:600">● ÉCOUTE ACTIVE</span>'
                '<p style="color:#9CA3AF;font-size:11px;margin:4px 0 0 0">Parlez maintenant…</p></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:rgba(243,156,18,0.1);border:1px solid rgba(243,156,18,0.25);border-radius:8px;padding:8px 12px;margin-bottom:8px">'
                f'<span style="color:#F39C12;font-size:12px;font-weight:600">● EN VEILLE</span>'
                f'<p style="color:#9CA3AF;font-size:11px;margin:4px 0 0 0">Dites « {config.WAKE_PHRASE_LABEL} »</p></div>',
                unsafe_allow_html=True,
            )
        if st.button("⏹  Arrêter l'écoute", use_container_width=True):
            listener.stop()
            st.session_state.stt_transcript = ""
            st.session_state.stt_message = ""
            st.rerun()
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
            state, message, intent = svc.handle(transcript, state)
            ui_state.save(state)
            # Si la commande modifie les filtres, forcer la recréation des widgets
            # (le key change → valeur pré-initialisée lue, sinon le widget ignore index=)
            if intent.action in ("filter", "reset", "clear_filter"):
                new_fv = st.session_state.get("filter_select_version", 0) + 1
                st.session_state.filter_select_version = new_fv
                st.session_state[f"sidebar_region_{new_fv}"] = state.filters.region or "Toutes"
                st.session_state[f"sidebar_categorie_{new_fv}"] = state.filters.categorie or "Toutes"
                # Idem pour le date picker si les dates ont changé
                p = intent.parameters or {}
                if p.get("date_start") or p.get("date_end") or intent.action in ("reset", "clear_filter"):
                    st.session_state.date_filter_version = st.session_state.get("date_filter_version", 0) + 1
            st.session_state.stt_message = message
            st.rerun()
        except _queue.Empty:
            pass
    else:
        if st.button("🎤  Démarrer l'écoute", use_container_width=True, type="primary"):
            listener.start(armed=True); st.rerun()
        if listener.wake_available:
            if st.button(f"🪄  Mains-libres (« {config.WAKE_PHRASE_LABEL} »)", use_container_width=True):
                listener.start(armed=False); st.rerun()
        else:
            st.caption("Mode mains-libres indisponible (openWakeWord non installé).")

    if st.session_state.stt_transcript:
        st.markdown(
            f'<p style="color:#9CA3AF;font-size:11px;margin:6px 0 0 0">💬 <em>{st.session_state.stt_transcript}</em></p>',
            unsafe_allow_html=True,
        )
    if st.session_state.stt_message:
        msg = st.session_state.stt_message
        (st.warning if "non reconnue" in msg.lower() else st.success)(msg)
    _commands_help()
