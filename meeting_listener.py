"""
meeting_listener.py — Real-time loopback audio capture + transcription.
Transcribes every CHUNK_SECONDS seconds while recording and calls on_text().
"""
from __future__ import annotations
import io, logging, threading, wave

logger = logging.getLogger(__name__)

SAMPLE_RATE   = 16000
CHUNK_SECONDS = 5   # transcribe every N seconds of audio


def _pcm_to_wav_bytes(samples_float32, sample_rate: int) -> bytes:
    import numpy as np
    pcm16 = (samples_float32 * 32767).clip(-32768, 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


def _transcribe_chunk(samples, language: str) -> str:
    import numpy as np
    import speech_recognition as sr

    peak = float(np.max(np.abs(samples)))
    if peak < 0.002:
        return ""

    gain = min(0.8 / peak, 6.0)
    samples = (samples * gain).clip(-1.0, 1.0)

    wav_bytes = _pcm_to_wav_bytes(samples, SAMPLE_RATE)
    recognizer = sr.Recognizer()
    try:
        audio = sr.AudioData(wav_bytes, SAMPLE_RATE, 2)
        return recognizer.recognize_google(audio, language=language).strip()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        logger.error("Google SR error: %s", e)
        return ""


def _capture_pyaudiowpatch(stop_event, on_chunk):
    import pyaudiowpatch as pyaudio
    import numpy as np

    p = pyaudio.PyAudio()
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        p.terminate()
        raise RuntimeError("WASAPI host API not available")

    default_spk = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

    device = None
    for lb in p.get_loopback_device_info_generator():
        if default_spk["name"] in lb["name"]:
            device = lb
            break
    if device is None:
        for lb in p.get_loopback_device_info_generator():
            device = lb
            break
    if device is None:
        p.terminate()
        raise RuntimeError("No WASAPI loopback device found")

    native_rate = int(device["defaultSampleRate"])
    channels    = max(1, int(device.get("maxInputChannels") or
                             device.get("maxOutputChannels") or 2))
    read_frames = native_rate  # read 1 second at a time

    logger.info("WASAPI loopback: '%s'  %d Hz  %d ch", device["name"], native_rate, channels)

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
            raw = stream.read(read_frames, exception_on_overflow=False)
            pcm = np.frombuffer(raw, dtype=np.int16).copy()
            if channels > 1:
                pcm = pcm.reshape(-1, channels).mean(axis=1).astype(np.int16)
            if native_rate != SAMPLE_RATE:
                n_new = int(len(pcm) * SAMPLE_RATE / native_rate)
                x_old = np.arange(len(pcm), dtype=np.float32)
                x_new = np.linspace(0, len(pcm) - 1, n_new, dtype=np.float32)
                pcm   = np.interp(x_new, x_old, pcm.astype(np.float32)).astype(np.int16)
            on_chunk(pcm.astype(np.float32) / 32767.0)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def _capture_soundcard(stop_event, on_chunk):
    import soundcard as sc
    import numpy as np

    devices = sc.all_microphones(include_loopback=True)
    device  = None
    for d in devices:
        if "loopback" in d.name.lower():
            device = d
            break
    if device is None and devices:
        device = devices[0]
    if device is None:
        raise RuntimeError("No loopback audio device found")

    logger.info("soundcard loopback: '%s'", device.name)
    with device.recorder(samplerate=SAMPLE_RATE, channels=1) as rec:
        while not stop_event.is_set():
            data    = rec.record(numframes=SAMPLE_RATE)
            samples = data[:, 0] if data.ndim > 1 else data
            on_chunk(samples.astype(np.float32))


class MeetingListener(threading.Thread):
    """
    Records loopback audio and transcribes in real-time every CHUNK_SECONDS.
    on_text(str) is called on the calling thread via the provided callback.
    """

    def __init__(self, on_text=None, language: str = "en-US"):
        super().__init__(daemon=True)
        self.language = language
        self.on_text  = on_text          # callback(text: str)
        self._stop    = threading.Event()
        self._buffer: list = []          # raw 1-second float32 chunks
        self._lock    = threading.Lock()

    def start_listening(self):
        self._stop.clear()
        with self._lock:
            self._buffer.clear()
        if not self.is_alive():
            self.start()

    def stop_listening(self):
        self._stop.set()

    def _flush_buffer(self):
        """Transcribe whatever is in the buffer and fire the callback."""
        import numpy as np
        with self._lock:
            if not self._buffer:
                return
            samples = np.concatenate(self._buffer)
            self._buffer.clear()

        text = _transcribe_chunk(samples, self.language)
        logger.info("Transcribed: %s", text or "<silent>")
        if text and self.on_text:
            self.on_text(text)

    def run(self):
        import numpy as np

        seconds_accumulated = 0

        def on_chunk(samples):
            nonlocal seconds_accumulated
            with self._lock:
                self._buffer.append(samples.copy())
            seconds_accumulated += 1
            if seconds_accumulated >= CHUNK_SECONDS:
                seconds_accumulated = 0
                threading.Thread(target=self._flush_buffer, daemon=True).start()

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

        # flush any remaining audio when stopped
        self._flush_buffer()
        logger.info("Meeting listener stopped")
