"""
meeting_listener.py — Captures system speaker audio via WASAPI loopback.
Records all audio while running; call transcribe_all() after stopping.
"""
from __future__ import annotations
import io, logging, threading, wave

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


# ── audio capture backends ────────────────────────────────────────────────────

def _capture_pyaudiowpatch(stop_event, on_chunk):
    """WASAPI loopback via pyaudiowpatch — primary on Windows."""
    import pyaudiowpatch as pyaudio
    import numpy as np

    p = pyaudio.PyAudio()
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        p.terminate()
        raise RuntimeError("WASAPI host API not available")

    default_spk = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

    # Find the loopback device that matches the default speaker
    device = None
    for lb in p.get_loopback_device_info_generator():
        if default_spk["name"] in lb["name"]:
            device = lb
            break
    # Fallback: use any available loopback
    if device is None:
        for lb in p.get_loopback_device_info_generator():
            device = lb
            break
    if device is None:
        p.terminate()
        raise RuntimeError("No WASAPI loopback device found")

    native_rate = int(device["defaultSampleRate"])
    # maxInputChannels for loopback mirrors the output device's channel count;
    # fall back to maxOutputChannels or 2 if it reads as 0
    channels = max(1, int(device.get("maxInputChannels") or
                          device.get("maxOutputChannels") or 2))
    chunk_frames = native_rate * 2  # 2-second read chunks

    logger.info("pyaudiowpatch loopback: '%s'  %d Hz  %d ch", device["name"], native_rate, channels)

    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=native_rate,
        input=True,
        input_device_index=device["index"],
        frames_per_buffer=1024,
    )
    try:
        while not stop_event.is_set():
            raw = stream.read(chunk_frames, exception_on_overflow=False)
            pcm = np.frombuffer(raw, dtype=np.int16).copy()
            if channels > 1:
                pcm = pcm.reshape(-1, channels).mean(axis=1).astype(np.int16)
            # Resample to 16 kHz via linear interpolation
            if native_rate != SAMPLE_RATE:
                n_new = int(len(pcm) * SAMPLE_RATE / native_rate)
                x_old = np.arange(len(pcm), dtype=np.float32)
                x_new = np.linspace(0, len(pcm) - 1, n_new, dtype=np.float32)
                pcm = np.interp(x_new, x_old, pcm.astype(np.float32)).astype(np.int16)
            on_chunk(pcm.astype(np.float32) / 32767.0)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def _capture_soundcard(stop_event, on_chunk):
    """Loopback via soundcard — fallback."""
    import soundcard as sc
    import numpy as np

    devices = sc.all_microphones(include_loopback=True)
    device = None
    for d in devices:
        if "loopback" in d.name.lower():
            device = d
            break
    if device is None:
        spk = sc.default_speaker().name[:12].lower()
        for d in devices:
            if spk in d.name.lower():
                device = d
                break
    if device is None and devices:
        device = devices[0]
    if device is None:
        raise RuntimeError("No loopback audio device found")

    logger.info("soundcard loopback: '%s'", device.name)
    with device.recorder(samplerate=SAMPLE_RATE, channels=1) as rec:
        while not stop_event.is_set():
            data = rec.record(numframes=SAMPLE_RATE * 2)
            samples = data[:, 0] if data.ndim > 1 else data
            on_chunk(samples.astype(np.float32))


# ── listener thread ───────────────────────────────────────────────────────────

class MeetingListener(threading.Thread):
    """
    Records loopback (speaker) audio while running.
    Usage:
        listener.start_listening()   # start recording
        listener.stop_listening()    # stop recording
        text = listener.transcribe_all()  # get full transcript
    """

    def __init__(self, language: str = "en-US"):
        super().__init__(daemon=True)
        self.language = language
        self._stop   = threading.Event()
        self._chunks: list = []
        self._lock   = threading.Lock()

    def start_listening(self):
        self._stop.clear()
        with self._lock:
            self._chunks.clear()
        if not self.is_alive():
            self.start()

    def stop_listening(self):
        self._stop.set()

    def transcribe_all(self) -> str:
        """Transcribe all recorded audio. Call after the thread has stopped."""
        with self._lock:
            chunks = list(self._chunks)

        if not chunks:
            logger.warning("No audio chunks recorded")
            return ""

        try:
            import numpy as np
            import speech_recognition as sr
        except ImportError as e:
            logger.error("Missing package: %s", e)
            return ""

        all_samples = np.concatenate(chunks)
        duration = len(all_samples) / SAMPLE_RATE
        logger.info("Transcribing %.1fs of audio", duration)

        # Normalise volume
        peak = float(np.max(np.abs(all_samples)))
        if peak < 0.001:
            logger.warning("Recording is silent (peak=%.5f)", peak)
            return ""
        gain = min(0.8 / peak, 6.0)
        all_samples = (all_samples * gain).clip(-1.0, 1.0)

        # Google SR works best on chunks ≤ 60 s; split if longer
        chunk_size = SAMPLE_RATE * 55  # 55-second segments
        segments = [all_samples[i:i + chunk_size]
                    for i in range(0, len(all_samples), chunk_size)]

        recognizer = sr.Recognizer()
        parts: list[str] = []
        for seg in segments:
            pcm16 = (seg * 32767).astype("<i2")
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(pcm16.tobytes())
            buf.seek(0)
            try:
                audio = sr.AudioData(buf.read(), SAMPLE_RATE, 2)
                text  = recognizer.recognize_google(audio, language=self.language).strip()
                if text:
                    parts.append(text)
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                logger.error("Google SR error: %s", e)

        result = " ".join(parts)
        logger.info("Transcript: %s", result)
        return result

    def run(self):
        def on_chunk(samples):
            with self._lock:
                self._chunks.append(samples.copy())

        try:
            _capture_pyaudiowpatch(self._stop, on_chunk)
        except ImportError:
            logger.warning("pyaudiowpatch not available, trying soundcard…")
            try:
                _capture_soundcard(self._stop, on_chunk)
            except Exception as exc:
                logger.exception("Audio capture failed: %s", exc)
        except Exception as exc:
            logger.warning("pyaudiowpatch failed (%s), trying soundcard…", exc)
            try:
                _capture_soundcard(self._stop, on_chunk)
            except Exception as exc2:
                logger.exception("Both audio backends failed: %s", exc2)

        logger.info("Meeting listener stopped — %d chunks recorded", len(self._chunks))
