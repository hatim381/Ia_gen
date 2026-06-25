"""Detecteur de mot-cle via openWakeWord. Degradation gracieuse si le paquet/modele manque.

WAKE_MODEL peut etre :
  - un mot-cle pre-entraine openWakeWord : "hey_jarvis", "alexa", "hey_mycroft"...
  - le chemin d'un modele custom .onnx/.tflite (ex. une phrase "ok dashboard" entrainee soi-meme,
    voir https://github.com/dscripka/openWakeWord pour l'entrainement d'un mot-cle personnalise).
"""
from __future__ import annotations
import os


class WakeWordDetector:
    def __init__(self, model: str, threshold: float = 0.5):
        self.threshold = threshold
        self._model = None
        self.available = False
        try:
            from openwakeword.model import Model
            if model and (model.endswith(".onnx") or model.endswith(".tflite")) and os.path.exists(model):
                self._model = Model(wakeword_models=[model])
            elif model:
                self._model = Model(wakeword_models=[model])
            else:
                self._model = Model()
            self.available = True
        except Exception:
            self.available = False

    def reset(self):
        try:
            if self._model:
                self._model.reset()
        except Exception:
            pass

    def detect(self, pcm16_bytes: bytes) -> bool:
        """pcm16_bytes : audio 16 kHz mono int16 (idealement ~1280 samples)."""
        if not self._model:
            return False
        try:
            import numpy as np
            audio = np.frombuffer(pcm16_bytes, dtype=np.int16)
            scores = self._model.predict(audio)
            return any(float(s) >= self.threshold for s in scores.values())
        except Exception:
            return False
