"""
core/serial_comm.py
====================
Fırının güç/röle kontrol kartıyla UART üzerinden konuşan katman.

Protokol (satır bazlı, '\\n' ile biter):

  Jetson -> Kart
    MODE:<AD>              örn. MODE:ALT_UST_FAN
    SETTEMP:<int>          örn. SETTEMP:200
    SETTIMER:<saniye>
    START
    STOP

  Kart -> Jetson
    TEMP:<int>             anlık iç sıcaklık
    DOOR:<0|1>              kapı durumu (1 = açık)
    STATUS:<IDLE|HEATING|READY|ERROR>
    ACK:<komut>

Gerçek kart bağlı değilse (veya pyserial/port bulunamazsa) ve
config.SERIAL_AUTO_SIMULATE = True ise, bu sınıf otomatik olarak
gerçekçi sahte telemetri üreten bir simülasyona düşer. Böylece
arayüz, donanım gelmeden önce Jetson üzerinde ya da bir PC'de
tam olarak test edilebilir.
"""

import time
import random
from PyQt5.QtCore import QThread, pyqtSignal

import config

try:
    import serial  # pyserial
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False


class SerialComm(QThread):
    # --- Kart -> UI sinyalleri ---
    temp_updated = pyqtSignal(int)
    door_changed = pyqtSignal(bool)
    status_updated = pyqtSignal(str)
    connection_changed = pyqtSignal(bool, str)   # (bağlı_mı, mesaj)

    def __init__(self, port=None, baudrate=None, parent=None):
        super().__init__(parent)
        self.port = port or config.SERIAL_PORT
        self.baudrate = baudrate or config.SERIAL_BAUDRATE
        self._running = False
        self._serial = None
        self._simulating = False

        # Simülasyon durumu
        self._sim_current_temp = 24
        self._sim_target_temp = 24
        self._sim_heating = False

        self._pending_writes = []

    # ------------------------------------------------------------------
    # Yaşam döngüsü
    # ------------------------------------------------------------------
    def run(self):
        self._running = True
        if PYSERIAL_AVAILABLE:
            try:
                self._serial = serial.Serial(
                    self.port, self.baudrate, timeout=config.SERIAL_TIMEOUT
                )
                self._simulating = False
                self.connection_changed.emit(True, f"{self.port} bağlı ({self.baudrate} baud)")
            except Exception as exc:
                if not config.SERIAL_AUTO_SIMULATE:
                    self.connection_changed.emit(False, f"Seri port hatası: {exc}")
                    return
                self._simulating = True
                self.connection_changed.emit(
                    False, "Kontrol kartı bulunamadı - simülasyon modu"
                )
        else:
            if not config.SERIAL_AUTO_SIMULATE:
                self.connection_changed.emit(False, "pyserial kurulu değil")
                return
            self._simulating = True
            self.connection_changed.emit(False, "pyserial yok - simülasyon modu")

        if self._simulating:
            self._run_simulation_loop()
        else:
            self._run_real_loop()

    def stop(self):
        self._running = False
        self.wait(1500)
        if self._serial and self._serial.is_open:
            self._serial.close()

    # ------------------------------------------------------------------
    # Gerçek donanım döngüsü
    # ------------------------------------------------------------------
    def _run_real_loop(self):
        while self._running:
            try:
                # Bekleyen komutları gönder
                while self._pending_writes:
                    cmd = self._pending_writes.pop(0)
                    self._serial.write((cmd + "\n").encode("utf-8"))

                line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    self._parse_line(line)
            except Exception as exc:
                self.connection_changed.emit(False, f"Bağlantı koptu: {exc}")
                time.sleep(1.0)

    def _parse_line(self, line: str):
        if line.startswith("TEMP:"):
            try:
                self.temp_updated.emit(int(line.split(":", 1)[1]))
            except ValueError:
                pass
        elif line.startswith("DOOR:"):
            self.door_changed.emit(line.split(":", 1)[1].strip() == "1")
        elif line.startswith("STATUS:"):
            self.status_updated.emit(line.split(":", 1)[1].strip())
        # ACK:... satırları şimdilik loglanmıyor, gerekirse eklenebilir.

    # ------------------------------------------------------------------
    # Simülasyon döngüsü (donanım yokken geliştirme için)
    # ------------------------------------------------------------------
    def _run_simulation_loop(self):
        self.status_updated.emit("IDLE")
        while self._running:
            while self._pending_writes:
                cmd = self._pending_writes.pop(0)
                self._apply_sim_command(cmd)

            if self._sim_heating:
                diff = self._sim_target_temp - self._sim_current_temp
                step = max(1, abs(diff) // 8) if diff != 0 else 0
                if diff > 0:
                    self._sim_current_temp += min(step, diff)
                elif diff < 0:
                    self._sim_current_temp += max(-step, diff)
                self._sim_current_temp += random.choice([-1, 0, 0, 1])
                if abs(self._sim_current_temp - self._sim_target_temp) <= 1:
                    self.status_updated.emit("READY")
            self.temp_updated.emit(int(self._sim_current_temp))
            time.sleep(1.0)

    def _apply_sim_command(self, cmd: str):
        if cmd.startswith("SETTEMP:"):
            self._sim_target_temp = int(cmd.split(":", 1)[1])
        elif cmd == "START":
            self._sim_heating = True
            self.status_updated.emit("HEATING")
        elif cmd == "STOP":
            self._sim_heating = False
            self.status_updated.emit("IDLE")
        # MODE / SETTIMER simülasyonda telemetriyi etkilemiyor, sadece kabul ediliyor.

    # ------------------------------------------------------------------
    # UI tarafından çağrılan komut gönderme API'si
    # ------------------------------------------------------------------
    def send_command(self, command: str):
        """Thread-safe komut kuyruğu. Ör: send_command('SETTEMP:200')"""
        self._pending_writes.append(command)

    @property
    def is_simulating(self) -> bool:
        return self._simulating
