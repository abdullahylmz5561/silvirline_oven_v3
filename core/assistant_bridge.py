"""
core/assistant_bridge.py
==========================
Sesli asistanın tüm parçalarını (uyandırma kelimesi, ses kaydı, bulut
STT/TTS, Claude ile sohbet + fırın kontrolü) tek bir yerden yöneten köprü.

Hem dokunmatik ekran hem sesli asistan fırını AYNI OvenController üzerinden
yönetir - assistant_bridge, Claude'un çağırdığı araçları (tool) o controller
çağrılarına çevirir.

Önemli: Bu artık sadece "aç/kapa" komutlarına cevap veren bir sistem DEĞİL.
Kullanıcı serbestçe sohbet edebilir, yemek tarifi isteyebilir - core/llm_assistant.py
bunları Claude API ile karşılar. Fırını GERÇEKTEN bir duruma getirmesi
gerektiğinde (ör. "pizza moduna al, başlat") Claude ilgili aracı çağırır,
o çağrı buradaki handle_intent() üzerinden OvenController'a gider.

İki tetikleme yolu var:
  1. Wake word ("Hey Silverline") -> WakeWordListener sürekli yerelde dinler,
     tetiklenince otomatik bir VoiceSession başlatır.
  2. Push-to-talk -> nav_rail'deki mikrofon butonuna basmak toggle_listening()
     çağırır, doğrudan bir VoiceSession başlatır (wake word beklenmez).

Her iki durumda da: wake word dinleyicisi ses kaydı sırasında DURAKLATILIR
(aynı mikrofona iki taraf birden erişemez), oturum bitince tekrar devam eder.

Sohbet geçmişi (self._conversation_history) oturumlar arasında burada
tutulur - böylece kullanıcı "peki onu 10 dakika daha pişirsem?" gibi
önceki cümleye bağlı bir şey söylediğinde Claude bağlamı hatırlar.
"""

import os

from PyQt5.QtCore import QObject, pyqtSignal

import config
from core.oven_controller import OvenController
from core.voice_session import VoiceSessionWorker

try:
    from core.wake_word import WakeWordListener
except ImportError:
    WakeWordListener = None


class AssistantBridge(QObject):
    # --- Dış dünyaya (UI) bildirilen durum sinyalleri ---
    state_changed = pyqtSignal(str)         # IDLE / LISTENING / PROCESSING / SPEAKING / ERROR
    transcript_ready = pyqtSignal(str)      # kullanıcının söylediği metin
    response_ready = pyqtSignal(str)        # asistanın yanıtı (toast/log için)
    assistant_unavailable = pyqtSignal(str)

    # Geriye dönük uyumluluk (nav_rail ilk sürümde bunlara bağlanmıştı)
    listening_started = pyqtSignal()
    listening_stopped = pyqtSignal()

    def __init__(self, oven_controller: OvenController, parent=None):
        super().__init__(parent)
        self.controller = oven_controller
        self.enabled = config.ASSISTANT_ENABLED
        self._session = None
        self._conversation_history = []   # Claude ile sohbet bağlamı (turlar arası korunur)

        self._intent_handlers = {
            "set_mode": self._handle_set_mode,
            "set_temperature": self._handle_set_temperature,
            "adjust_temperature": self._handle_adjust_temperature,
            "apply_recipe": self._handle_apply_recipe,
            "start_cooking": lambda p: self.controller.start(),
            "stop_cooking": lambda p: self.controller.stop(),
            "set_timer": self._handle_set_timer,
        }

        self.wake_word = None
        if self.enabled and config.WAKE_WORD_ENABLED and WakeWordListener is not None:
            self.wake_word = WakeWordListener()
            self.wake_word.wake_detected.connect(self._start_session)
            self.wake_word.error.connect(self._on_wake_word_error)
            self.wake_word.start()

    # ------------------------------------------------------------------
    # Tetikleme giriş noktaları
    # ------------------------------------------------------------------
    def toggle_listening(self):
        """Nav rail'deki mikrofon düğmesine basıldığında (push-to-talk)."""
        if not self.enabled:
            self.assistant_unavailable.emit(
                "Sesli asistan devre dışı. config.ASSISTANT_ENABLED = True yapıp "
                "Google Cloud kimlik bilgilerini tanımlayın."
            )
            return
        if config.LLM_ENABLED and not os.environ.get("ANTHROPIC_API_KEY"):
            self.assistant_unavailable.emit(
                "ANTHROPIC_API_KEY ortam değişkeni tanımlı değil - Claude API'ye "
                "bağlanılamıyor."
            )
            return
        if self._session is not None:
            return  # zaten bir oturum sürüyor, yeni buton basışını yok say
        self._start_session()

    def _start_session(self):
        if self._session is not None:
            return
        if self.wake_word:
            self.wake_word.pause()

        self._session = VoiceSessionWorker(
            intent_handler=self.handle_intent,
            history=self._conversation_history,
        )
        self._session.state_changed.connect(self._on_state_changed)
        self._session.transcript_ready.connect(self.transcript_ready)
        self._session.response_ready.connect(self.response_ready)
        self._session.history_updated.connect(self._on_history_updated)
        self._session.finished.connect(self._on_session_finished)
        self._session.start()

    def _on_history_updated(self, history):
        self._conversation_history = history

    def _on_session_finished(self):
        self._session = None
        if self.wake_word:
            self.wake_word.resume()

    def _on_state_changed(self, state: str):
        self.state_changed.emit(state)
        if state == "LISTENING":
            self.listening_started.emit()
        elif state in ("DONE", "ERROR"):
            self.listening_stopped.emit()

    def _on_wake_word_error(self, message: str):
        self.assistant_unavailable.emit(message)

    # ------------------------------------------------------------------
    # Claude'un çağırdığı araçları OvenController'a uygulama
    # ------------------------------------------------------------------
    def handle_intent(self, intent_name: str, params: dict):
        """core/llm_assistant.py buradan çağırır: Claude bir aracı
        kullanmaya karar verdiğinde tek giriş noktası budur."""
        handler = self._intent_handlers.get(intent_name)
        if handler is None:
            return
        handler(params or {})

    def _handle_set_mode(self, params):
        mode = params.get("mode")
        if mode:
            self.controller.set_mode(mode)

    def _handle_set_temperature(self, params):
        value = params.get("value")
        if value is not None:
            self.controller.set_target_temp(int(value))

    def _handle_adjust_temperature(self, params):
        delta = params.get("delta", 0)
        self.controller.adjust_temp(int(delta))

    def _handle_apply_recipe(self, params):
        self.controller.apply_recipe(
            params["mode"], params["temp"], params["minutes"]
        )

    def _handle_set_timer(self, params):
        minutes = params.get("minutes")
        if minutes is not None:
            self.controller.set_timer(int(minutes) * 60)

    # ------------------------------------------------------------------
    def shutdown(self):
        if self.wake_word:
            self.wake_word.stop()
        if self._session:
            self._session.wait(2000)
