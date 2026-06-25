import tempfile
from pathlib import Path

import streamlit as st

# Biais Whisper vers le vocabulaire du dashboard : réduit les erreurs de transcription
# sur les mots-clés de navigation et les entités métier.
WHISPER_PROMPT = (
    "Accueil, Vue globale, Performance, Régions, Reset, Réinitialiser, "
    "Résumé, Synthèse, Aide, Nord, Sud, Est, Ouest, Île-de-France, "
    "Électronique, Vêtements, Alimentation, Maison, Sport, "
    "Affiche, Ventes, Catégorie, Région, Filtre, "
    "Janvier, Février, Mars, Avril, Mai, Juin, "
    "Juillet, Août, Septembre, Octobre, Novembre, Décembre"
)


@st.cache_resource(show_spinner="Chargement du modèle Whisper…")
def _load_whisper_model():
    from faster_whisper import WhisperModel
    # int8 : quantification 8 bits → 4-8x plus rapide que openai-whisper sur CPU, même qualité
    return WhisperModel("base", device="cpu", compute_type="int8")


def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcrit un flux audio (bytes WAV) en texte via faster-whisper local."""
    model = _load_whisper_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, _ = model.transcribe(
            tmp_path,
            language="fr",
            initial_prompt=WHISPER_PROMPT,
            vad_filter=True,
            beam_size=1,
            condition_on_previous_text=False,
            temperature=0,
        )
        return " ".join(seg.text for seg in segments).strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)
