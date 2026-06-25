import io
import queue
import threading
import wave

# Identique à transcriber.WHISPER_PROMPT — dupliqué pour éviter un import Streamlit
# depuis le thread background (st.cache_resource s'exécute hors contexte Streamlit).
WHISPER_PROMPT = (
    "Accueil, Vue globale, Performance, Régions, Reset, Réinitialiser, "
    "Résumé, Synthèse, Aide, Nord, Sud, Est, Ouest, Île-de-France, "
    "Électronique, Vêtements, Alimentation, Maison, Sport, "
    "Affiche, Ventes, Catégorie, Région, Filtre, "
    "Janvier, Février, Mars, Avril, Mai, Juin, "
    "Juillet, Août, Septembre, Octobre, Novembre, Décembre"
)

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 480 samples = 960 bytes int16
SILENCE_FRAMES = 20   # 600ms de silence pour clore un segment
MIN_SPEECH_FRAMES = 5  # 150ms minimum pour ignorer les bruits courts
POST_TRANSCRIPTION_COOLDOWN = 30  # 900ms de frames à ignorer après transcription


def _frames_to_wav(frames: list[bytes]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


# Singleton Whisper hors contexte Streamlit (thread background sans session)
_whisper_model = None
_whisper_lock = threading.Lock()


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        with _whisper_lock:
            if _whisper_model is None:
                from faster_whisper import WhisperModel
                _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


class MicListener:
    def __init__(self):
        import webrtcvad
        self._vad = webrtcvad.Vad(2)  # aggressivité 0-3 : 2 = équilibre parole/bruit
        self._running = False
        self._thread: threading.Thread | None = None
        self._error: str = ""
        self.transcript_queue: queue.Queue[str] = queue.Queue()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def error(self) -> str:
        return self._error

    def start(self) -> None:
        if self._running:
            return
        self._error = ""
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _transcribe(self, frames: list[bytes]) -> None:
        import tempfile
        from pathlib import Path

        model = _get_whisper_model()
        wav_bytes = _frames_to_wav(frames)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
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
            text = " ".join(seg.text for seg in segments).strip()
            if text:
                self.transcript_queue.put(text)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _listen_loop(self) -> None:
        try:
            import sounddevice as sd
        except (ImportError, OSError) as exc:
            self._error = str(exc)
            self._running = False
            return

        speech_frames: list[bytes] = []
        silence_count = 0
        in_speech = False
        cooldown = 0

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=FRAME_SAMPLES,
            ) as stream:
                while self._running:
                    data, _ = stream.read(FRAME_SAMPLES)
                    frame = bytes(data)

                    # webrtcvad exige exactement FRAME_SAMPLES * 2 bytes
                    if len(frame) != FRAME_SAMPLES * 2:
                        continue

                    # Purge les frames accumulées pendant la transcription
                    if cooldown > 0:
                        cooldown -= 1
                        continue

                    try:
                        is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
                    except Exception:
                        continue

                    if is_speech:
                        in_speech = True
                        silence_count = 0
                        speech_frames.append(frame)
                    elif in_speech:
                        silence_count += 1
                        speech_frames.append(frame)

                        if silence_count >= SILENCE_FRAMES:
                            if len(speech_frames) >= MIN_SPEECH_FRAMES:
                                self._transcribe(speech_frames)
                                cooldown = POST_TRANSCRIPTION_COOLDOWN
                            speech_frames = []
                            silence_count = 0
                            in_speech = False

        except Exception as exc:
            self._error = str(exc)
            self._running = False
