"""Moteur de transcription Whisper (faster-whisper) — pur, sans capture ni UI."""
from __future__ import annotations
import tempfile, threading
from pathlib import Path

from core import config

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from faster_whisper import WhisperModel
                _model = WhisperModel(config.WHISPER_MODEL, device="cpu",
                                      compute_type=config.WHISPER_COMPUTE)
    return _model


def transcribe(audio: bytes | str) -> str:
    """audio = bytes WAV ou chemin de fichier."""
    model = _get_model()
    tmp_path = None
    try:
        if isinstance(audio, bytes):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio); tmp_path = tmp.name
            src = tmp_path
        else:
            src = audio
        segments, _ = model.transcribe(
            src, language="fr", initial_prompt=config.WHISPER_PROMPT,
            vad_filter=True, beam_size=1, condition_on_previous_text=False, temperature=0,
            no_speech_threshold=0.6, log_prob_threshold=-1.0, compression_ratio_threshold=2.4,
        )
        parts = []
        for s in segments:
            # Filtre les hallucinations : prob silence élevée, texte répétitif, ou logprob faible
            if s.no_speech_prob > 0.6:
                continue
            if s.compression_ratio > 2.4:
                continue
            if s.avg_logprob < -1.0:
                continue
            parts.append(s.text)
        return " ".join(parts).strip()
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
