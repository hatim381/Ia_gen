"""Capture micro + VAD + (optionnel) wake-word, en thread background.
Decouple du moteur Whisper (engine) et de l'UI : pousse transcriptions et evenements
dans des files que l'UI depile. Deux modes : 'arme' (commandes) ou 'veille' (attend le mot-cle)."""
from __future__ import annotations
import io, queue, threading, wave

from core import config
from core.stt import engine

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 480
SILENCE_FRAMES = 20
MIN_SPEECH_FRAMES = 5
POST_TRANSCRIPTION_COOLDOWN = 30
WAKE_CHUNK = 1280  # samples (~80ms) recommande par openWakeWord


def _frames_to_wav(frames: list[bytes]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


class MicListener:
    def __init__(self):
        import webrtcvad
        self._vad = webrtcvad.Vad(2)
        self._running = False
        self._armed = False
        self._thread: threading.Thread | None = None
        self._error = ""
        self.transcript_queue: queue.Queue[str] = queue.Queue()
        self.status_queue: queue.Queue[str] = queue.Queue()
        self._wake = None
        if config.WAKE_ENABLED:
            try:
                from core.stt.wakeword import WakeWordDetector
                det = WakeWordDetector(config.WAKE_MODEL, config.WAKE_THRESHOLD)
                self._wake = det if det.available else None
            except Exception:
                self._wake = None

    @property
    def is_running(self) -> bool: return self._running
    @property
    def armed(self) -> bool: return self._armed
    @property
    def error(self) -> str: return self._error
    @property
    def wake_available(self) -> bool: return self._wake is not None

    def start(self, armed: bool = False):
        if self._running: return
        self._error = ""; self._running = True; self._armed = armed
        self._thread = threading.Thread(target=self._loop, daemon=True); self._thread.start()

    def stop(self):
        self._running = False; self._armed = False

    def _transcribe(self, frames):
        text = engine.transcribe(_frames_to_wav(frames))
        if text:
            self.transcript_queue.put(text)

    def _loop(self):
        try:
            import sounddevice as sd
        except (ImportError, OSError) as exc:
            self._error = str(exc); self._running = False; return
        speech, silence, in_speech, cooldown = [], 0, False, 0
        wake_buf = bytearray()
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                   blocksize=FRAME_SAMPLES) as stream:
                while self._running:
                    data, _ = stream.read(FRAME_SAMPLES); frame = bytes(data)
                    if len(frame) != FRAME_SAMPLES * 2:
                        continue

                    # --- Mode VEILLE : on attend le mot-cle ---
                    if not self._armed:
                        if self._wake is None:
                            continue
                        wake_buf.extend(frame)
                        while len(wake_buf) >= WAKE_CHUNK * 2:
                            chunk = bytes(wake_buf[:WAKE_CHUNK * 2]); del wake_buf[:WAKE_CHUNK * 2]
                            if self._wake.detect(chunk):
                                self._armed = True; wake_buf.clear()
                                self._wake.reset()
                                self.status_queue.put("wake")
                                break
                        continue

                    # --- Mode ARME : capture + transcription des commandes ---
                    if cooldown > 0:
                        cooldown -= 1; continue
                    try:
                        is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
                    except Exception:
                        continue
                    if is_speech:
                        in_speech = True; silence = 0; speech.append(frame)
                    elif in_speech:
                        silence += 1; speech.append(frame)
                        if silence >= SILENCE_FRAMES:
                            if len(speech) >= MIN_SPEECH_FRAMES:
                                self._transcribe(speech); cooldown = POST_TRANSCRIPTION_COOLDOWN
                            speech, silence, in_speech = [], 0, False
        except Exception as exc:
            self._error = str(exc); self._running = False
