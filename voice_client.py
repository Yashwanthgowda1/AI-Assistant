"""
voice_client.py — Background thread for continuous voice recognition.
Emits recognised text via a Qt signal callback.
Uses Google Web Speech API (free, no key needed for basic use).
"""
from __future__ import annotations
import logging, threading, queue
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class VoiceListener(threading.Thread):
    """
    Runs in a daemon thread.
    Calls `on_text(text: str)` in the calling thread via a thread-safe queue.
    """

    def __init__(self, on_text: Callable[[str], None], language: str = "en-US"):
        super().__init__(daemon=True)
        self.on_text = on_text
        self.language = language
        self._stop_event = threading.Event()
        self._q: queue.Queue[str] = queue.Queue()
        self._recognizer = None
        self._mic = None

    # ── public API ───────────────────────────────────────────────
    def start_listening(self):
        self._stop_event.clear()
        if not self.is_alive():
            self.start()

    def stop_listening(self):
        self._stop_event.set()

    def drain(self):
        """Call from the main thread (e.g. a QTimer) to dispatch queued text."""
        while not self._q.empty():
            try:
                self.on_text(self._q.get_nowait())
            except queue.Empty:
                break

    # ── thread body ──────────────────────────────────────────────
    def run(self):
        try:
            import speech_recognition as sr
        except ImportError:
            logger.error("SpeechRecognition not installed; pip install SpeechRecognition pyaudio")
            return

        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        r.pause_threshold = 1.0

        try:
            mic = sr.Microphone()
        except OSError:
            logger.error("No microphone found.")
            return

        logger.info("Voice listener started (lang=%s)", self.language)
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=1)
            while not self._stop_event.is_set():
                try:
                    audio = r.listen(source, timeout=5, phrase_time_limit=30)
                    text = r.recognize_google(audio, language=self.language)
                    if text.strip():
                        logger.info("Voice: %s", text)
                        self._q.put(text.strip())
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    logger.warning("Google SR error: %s", e)
                    continue
                except Exception as exc:
                    logger.exception("Voice error: %s", exc)
                    break

        logger.info("Voice listener stopped.")
