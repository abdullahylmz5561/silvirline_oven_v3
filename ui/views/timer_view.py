"""
ui/views/timer_view.py
=========================
Bağımsız geri sayım zamanlayıcısı. Fırın çalışırken de, çalışmıyorken de
kullanılabilir (örn. dinlendirme süresi için). controller.set_timer ile
kontrol kartına da SETTIMER komutu gönderilir.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer


PRESETS_MIN = [5, 10, 15, 30]


class TimerView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.remaining = PRESETS_MIN[1] * 60
        self.running = False

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setSpacing(22)

        self.display = QLabel(self._format(self.remaining))
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setStyleSheet(
            "font-family:'JetBrains Mono'; font-size:72px; font-weight:700; color:#f0a860;"
        )
        root.addWidget(self.display)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        preset_row.setAlignment(Qt.AlignCenter)
        self.preset_buttons = []
        for m in PRESETS_MIN:
            btn = QPushButton(f"{m} dk")
            btn.setProperty("class", "chip")
            btn.setCheckable(True)
            btn.setChecked(m == PRESETS_MIN[1])
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, mm=m: self._set_preset(mm))
            preset_row.addWidget(btn)
            self.preset_buttons.append(btn)
        root.addLayout(preset_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(14)
        ctrl_row.setAlignment(Qt.AlignCenter)
        reset_btn = QPushButton("Sıfırla")
        reset_btn.setProperty("class", "ghostBtn")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset)
        self.toggle_btn = QPushButton("Başlat")
        self.toggle_btn.setProperty("class", "emberBtn")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle)
        ctrl_row.addWidget(reset_btn)
        ctrl_row.addWidget(self.toggle_btn)
        root.addLayout(ctrl_row)

        self._qtimer = QTimer(self)
        self._qtimer.timeout.connect(self._tick)

    def _format(self, seconds):
        m, s = divmod(max(0, seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _set_preset(self, minutes):
        for btn in self.preset_buttons:
            btn.setChecked(btn.text() == f"{minutes} dk")
        self.remaining = minutes * 60
        self.display.setText(self._format(self.remaining))

    def _toggle(self):
        self.running = not self.running
        if self.running:
            self.controller.set_timer(self.remaining)
            self._qtimer.start(1000)
            self.toggle_btn.setText("Duraklat")
        else:
            self._qtimer.stop()
            self.toggle_btn.setText("Devam Et")

    def _reset(self):
        self._qtimer.stop()
        self.running = False
        self.toggle_btn.setText("Başlat")
        checked = next((b for b in self.preset_buttons if b.isChecked()), None)
        minutes = int(checked.text().split()[0]) if checked else PRESETS_MIN[1]
        self.remaining = minutes * 60
        self.display.setText(self._format(self.remaining))

    def _tick(self):
        self.remaining -= 1
        self.display.setText(self._format(self.remaining))
        if self.remaining <= 0:
            self._qtimer.stop()
            self.running = False
            self.toggle_btn.setText("Başlat")
