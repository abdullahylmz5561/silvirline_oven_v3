"""
core/oven_controller.py
========================
Fırının tek "gerçek durum" (single source of truth) katmanı.

Hem dokunmatik arayüz butonları hem de ileride eklenecek sesli asistan
(bkz. assistant_bridge.py) fırını DOĞRUDAN seri porta yazmak yerine
HER ZAMAN bu sınıf üzerinden yönetir. Böylece:
  - UI, kart protokolünü bilmek zorunda kalmaz.
  - Sesli asistan geldiğinde sadece bu sınıfın metodlarını çağırması yeterli
    olur, ayrı bir entegrasyon yapmaya gerek kalmaz.
"""

from PyQt5.QtCore import QObject, pyqtSignal

import config
from core.serial_comm import SerialComm


# Fırın fonksiyonları: (anahtar, görünen ad, varsayılan sıcaklık)
OVEN_FUNCTIONS = [
    {"key": "ALT",          "label": "Alt",              "temp": 170},
    {"key": "ALT_UST",      "label": "Alt - Üst",        "temp": 180},
    {"key": "ALT_UST_FAN",  "label": "Alt - Üst Fan",    "temp": 180},
    {"key": "PIZZA",        "label": "Pizza",            "temp": 220},
    {"key": "GRILL",        "label": "Izgara",           "temp": 230},
    {"key": "MAXI_GRILL",   "label": "Maksi Izgara",     "temp": 220},
]


class OvenController(QObject):
    # --- UI'ın dinleyeceği sinyaller ---
    mode_changed = pyqtSignal(str)             # yeni mod anahtarı
    target_temp_changed = pyqtSignal(int)
    current_temp_changed = pyqtSignal(int)
    running_changed = pyqtSignal(bool)
    status_changed = pyqtSignal(str)            # IDLE / HEATING / READY / ERROR
    door_changed = pyqtSignal(bool)
    connection_changed = pyqtSignal(bool, str)
    timer_seconds_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = OVEN_FUNCTIONS[1]["key"]          # varsayılan: ALT_UST
        self.target_temp = OVEN_FUNCTIONS[1]["temp"]
        self.current_temp = 24
        self.is_running = False
        self.timer_seconds = 0

        self.serial = SerialComm()
        self.serial.temp_updated.connect(self._on_temp_updated)
        self.serial.door_changed.connect(self.door_changed)
        self.serial.status_updated.connect(self.status_changed)
        self.serial.connection_changed.connect(self.connection_changed)
        self.serial.start()

    # ------------------------------------------------------------------
    def _on_temp_updated(self, value: int):
        self.current_temp = value
        self.current_temp_changed.emit(value)

    # ------------------------------------------------------------------
    # Komutlar - UI ve (ileride) sesli asistan bu metodları çağırır
    # ------------------------------------------------------------------
    def set_mode(self, mode_key: str):
        func = next((f for f in OVEN_FUNCTIONS if f["key"] == mode_key), None)
        if not func:
            return
        self.mode = mode_key
        self.target_temp = func["temp"]
        self.mode_changed.emit(mode_key)
        self.target_temp_changed.emit(self.target_temp)
        self.serial.send_command(f"MODE:{mode_key}")
        self.serial.send_command(f"SETTEMP:{self.target_temp}")

    def set_target_temp(self, value: int):
        value = max(config.MIN_TEMP, min(config.MAX_TEMP, value))
        self.target_temp = value
        self.target_temp_changed.emit(value)
        self.serial.send_command(f"SETTEMP:{value}")

    def adjust_temp(self, delta: int):
        self.set_target_temp(self.target_temp + delta)

    def apply_recipe(self, mode_key: str, temp: int, minutes: int):
        """Tarif ekranından bir yemek seçildiğinde çağrılır."""
        self.set_mode(mode_key)
        self.set_target_temp(temp)
        self.set_timer(minutes * 60)

    def set_timer(self, seconds: int):
        self.timer_seconds = max(0, seconds)
        self.timer_seconds_changed.emit(self.timer_seconds)
        self.serial.send_command(f"SETTIMER:{self.timer_seconds}")

    def start(self):
        self.is_running = True
        self.running_changed.emit(True)
        self.serial.send_command("START")

    def stop(self):
        self.is_running = False
        self.running_changed.emit(False)
        self.serial.send_command("STOP")

    def toggle_start_stop(self):
        self.stop() if self.is_running else self.start()

    def shutdown(self):
        self.serial.stop()
