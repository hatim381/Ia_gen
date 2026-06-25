"""Capture micro + VAD, en thread background. Decouple du moteur Whisper (engine)
et de l'UI : pousse les transcriptions dans une file que l'UI depile."""
from __future__ import annotations
import io, queue, threading, wave

from core.stt import engine

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)
SILENCE_FRAMES = 20
MIN_SPEECH_FRAMES = 5
POST_TRANSCRIPTION_COOLDOWN = 30


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
        self._thread: threading.Thread | None = None
        self._error = ""
        self.transcript_queue: queue.Queue[str] = queue.Queue()

    @property
    def is_running(self) -> bool: return self._running
    @property
    def error(self) -> str: return self._error

    def start(self):
        if self._running: return
        self._error = ""; self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True); self._thread.start()

    def stop(self): self._running = False

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
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                   blocksize=FRAME_SAMPLES) as stream:
                while self._running:
                    data, _ = stream.read(FRAME_SAMPLES); frame = bytes(data)
                    if len(frame) != FRAME_SAMPLES * 2: continue
                    if cooldown > 0: cooldown -= 1; continue
                    try: is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
                    except Exception: continue
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
