"""
core/voice_session.py
========================
Tek bir sesli alışverişi uçtan uca yürüten QThread.

Akış: ses kaydı (VAD ile) -> Google STT -> Claude API (sohbet + gerekirse
fırın araç çağrısı) -> Google TTS -> hoparlörden çalma.

Neden ayrı thread: kayıt, ağ istekleri (STT/LLM/TTS) ve ses çalma hepsi
saniyeler sürebilecek BLOKLAYICI işlemler. SerialComm'da kullanılan aynı
QThread + sinyal deseni burada da uygulanıyor, UI asla kilitlenmez.
"""

from PyQt5.QtCore import QThread, pyqtSignal

from core import audio_io, cloud_speech, llm_assistant


class VoiceSessionWorker(QThread):
    state_changed = pyqtSignal(str)       # LISTENING / PROCESSING / SPEAKING / DONE / ERROR
    transcript_ready = pyqtSignal(str)     # kullanıcının söylediği metin
    response_ready = pyqtSignal(str)       # asistanın sesli/yazılı yanıtı
    history_updated = pyqtSignal(list)     # bir sonraki tur için sohbet geçmişi

    def __init__(self, intent_handler, history=None, parent=None):
        super().__init__(parent)
        self._intent_handler = intent_handler
        self._history = history or []

    def run(self):
        try:
            self.state_changed.emit("LISTENING")
            pcm_audio = audio_io.record_until_silence()

            self.state_changed.emit("PROCESSING")
            transcript = cloud_speech.speech_to_text(pcm_audio)
            self.transcript_ready.emit(transcript)

            if not transcript:
                response = "Sizi duyamadım, tekrar deneyebilir misiniz?"
                new_history = self._history
            else:
                # Claude burada hem serbestçe sohbet edip tarif önerebiliyor
                # hem de gerekirse fırın araçlarını çağırıyor (intent_handler
                # üzerinden - bu OvenController'a gider, dokunmatik ekranla
                # tamamen aynı yoldan).
                response, new_history = llm_assistant.generate_reply(
                    transcript, self._history, self._intent_handler
                )

            self.response_ready.emit(response)
            self.history_updated.emit(new_history)

            self.state_changed.emit("SPEAKING")
            audio_bytes, sample_rate = cloud_speech.text_to_speech(response)
            audio_io.play_pcm(audio_bytes, sample_rate)

            self.state_changed.emit("DONE")

        except Exception as exc:
            self.state_changed.emit("ERROR")
            self.response_ready.emit(f"Bir hata oluştu: {exc}")
