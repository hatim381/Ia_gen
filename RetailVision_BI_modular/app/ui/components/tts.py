"""TTS navigateur via Web Speech API (SpeechSynthesis). Local (voix de l'OS), aucune dependance.
Genere un petit script qui lit le texte en francais. Rendu uniquement quand demande."""
from __future__ import annotations
import json
import streamlit as st
import streamlit.components.v1 as components


def speak(text: str):
    """Lit le texte a voix haute dans le navigateur (voix fr-FR si disponible)."""
    if not text:
        return
    payload = json.dumps(text)
    components.html(
        f"""
        <script>
        const text = {payload};
        function frenchVoice() {{
            const voices = window.speechSynthesis.getVoices();
            return voices.find(v => v.lang && v.lang.toLowerCase().startsWith('fr')) || null;
        }}
        function say() {{
            const u = new SpeechSynthesisUtterance(text);
            u.lang = 'fr-FR';
            const v = frenchVoice();
            if (v) u.voice = v;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
        }}
        if (window.speechSynthesis.getVoices().length) say();
        else window.speechSynthesis.onvoiceschanged = say;
        </script>
        """,
        height=0,
    )


def read_button(text: str, key: str, label: str = "🔊 Lire"):
    """Bouton qui declenche la lecture du texte fourni."""
    if not text:
        return
    if st.button(label, key=key):
        speak(text)
