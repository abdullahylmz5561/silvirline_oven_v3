"""
core/wake_word.py
====================
"Hey Silverline" uyandırma kelimesini YERELDE (offline) dinleyen thread.

Neden yerel: sürekli mikrofon akışını buluta göndermek hem maliyetli hem
gecikmeli hem de mahremiyet açısından uygun değil. Bu yüzden yalnızca
uyandırma kelimesi tespit edildikten SONRAKİ komut cümlesi bulut STT'ye
gönderiliyor (bkz. assistant_bridge.py).

openWakeWord (açık kaynak, ücretsiz) kullanılıyor. Özel "Hey Silverline"
modelini eğitmek için: https://github.com/dscripka/openWakeWord
(birkaç dakikalık sentetik veri ile eğitim yapılabiliyor, GPU gerekmez).
Model dosyasını config.WAKE_WORD_MODEL_PATH konumuna yerleştirin.

Bu thread, VoiceSessionWorker ses kaydı yaparken MUTLAKA duraklatılmalı
(pause()) - aksi halde iki taraf aynı anda mikrofon donanımına erişmeye
çalışır. Bu yönetim assistant_bridge.py içinde yapılıyor.
"""

import queue

import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QThread, pyqtSignal

import config

try:
    from openwakeword.model import Model as OWWModel
    OWW_AVAILABLE = True
except ImportError:
    OWW_AVAILABLE = False


class WakeWordListener(QThread):
    wake_detected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._paused = False
        self._model = None

    def run(self):
        if not OWW_AVAILABLE:
            self.error.emit("openwakeword kurulu değil - uyandırma kelimesi devre dışı")
            return
        try:
            self._model = OWWModel(wakeword_models=[config.WAKE_WORD_MODEL_PATH])
        except Exception as exc:
            self.error.emit(f"Uyandırma kelimesi modeli yüklenemedi: {exc}")
            return

        self._running = True
        chunk_samples = 1280  # openWakeWord'ün beklediği tipik çerçeve boyutu (80ms @16kHz)
        audio_q = queue.Queue()

        def callback(indata, frames, time_info, status):
            if not self._paused:
                audio_q.put(indata.copy())

        with sd.InputStream(
            samplerate=config.AUDIO_SAMPLE_RATE,
            blocksize=chunk_samples,
            device=config.MIC_DEVICE_INDEX,
            dtype="int16",
            channels=config.AUDIO_CHANNELS,
            callback=callback,
        ):
            while self._running:
                try:
                    chunk = audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if self._paused:
                    continue

                audio = np.squeeze(chunk)
                predictions = self._model.predict(audio)
                score = max(predictions.values()) if predictions else 0.0
                if score >= config.WAKE_WORD_THRESHOLD:
                    self.wake_detected.emit()
                    # Kendi kendini tetiklemesini önlemek için kısa süreliğine duraklat;
                    # assistant_bridge zaten pause() çağıracak ama emin olalım.
                    self.pause()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False
        self.wait(1500)
