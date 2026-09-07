"""
ui/views/home_view.py
========================
Ana ekran. Kullanıcının fırını en sık yaptığı iş burada:
  - Solda: hedef sıcaklık kadranı, +/- ayar, Başlat/Durdur.
  - Sağda: fırın fonksiyonları (Alt, Alt-Üst, Alt-Üst Fan, Pizza,
    Izgara, Maksi Izgara) - her biri gerçek fırın piktogramıyla.

Tarifler burada YOK; onlara sol menüden ayrı bir ekran olarak ulaşılıyor
(bkz. recipes_view.py) - kullanıcının isteği doğrultusunda.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt

from ui.widgets.temp_dial import TempDial
from ui.icons import OvenFunctionIcon
from core.oven_controller import OVEN_FUNCTIONS


class FunctionCard(QFrame):
    def __init__(self, func, on_click, parent=None):
        super().__init__(parent)
        self.func = func
        self.setProperty("class", "card")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.icon = OvenFunctionIcon(func["key"], size=34)
        layout.addWidget(self.icon, alignment=Qt.AlignLeft)

        name = QLabel(func["label"])
        name.setProperty("class", "funcName")
        layout.addWidget(name)

        temp = QLabel(f'{func["temp"]}°C önerilen')
        temp.setProperty("class", "dim")
        layout.addWidget(temp)

        self._on_click = on_click

    def mousePressEvent(self, _event):
        self._on_click(self.func["key"])

    def set_selected(self, selected: bool):
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon.set_active(selected)


class HomeView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.cards = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(22)

        # ---- Sol: kadran paneli ----
        dial_pane = QVBoxLayout()
        dial_pane.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        dial_pane.setSpacing(10)

        self.dial = TempDial()
        dial_pane.addWidget(self.dial, alignment=Qt.AlignHCenter)

        self.mode_label = QLabel("Alt - Üst")
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setStyleSheet("color:#a89f93; font-size:11px; letter-spacing:1.5px; text-transform:uppercase;")
        dial_pane.addWidget(self.mode_label)

        adj_row = QHBoxLayout()
        adj_row.setSpacing(18)
        minus_btn = QPushButton("−")
        minus_btn.setProperty("class", "roundAdj")
        minus_btn.clicked.connect(lambda: self.controller.adjust_temp(-10))
        plus_btn = QPushButton("+")
        plus_btn.setProperty("class", "roundAdj")
        plus_btn.clicked.connect(lambda: self.controller.adjust_temp(10))
        adj_row.addWidget(minus_btn)
        adj_row.addWidget(plus_btn)
        dial_pane.addLayout(adj_row)

        self.current_temp_label = QLabel("Anlık: 24°C")
        self.current_temp_label.setProperty("class", "dim")
        self.current_temp_label.setAlignment(Qt.AlignCenter)
        dial_pane.addWidget(self.current_temp_label)

        self.start_btn = QPushButton("Pişirmeyi Başlat")
        self.start_btn.setProperty("class", "emberBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.controller.toggle_start_stop)
        dial_pane.addSpacing(6)
        dial_pane.addWidget(self.start_btn)

        dial_container = QWidget()
        dial_container.setFixedWidth(240)
        dial_container.setLayout(dial_pane)
        root.addWidget(dial_container)

        # ---- Sağ: fonksiyon ızgarası ----
        right = QVBoxLayout()
        right.setSpacing(12)

        title = QLabel("Fırın Fonksiyonları")
        title.setProperty("class", "title")
        right.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)
        for i, func in enumerate(OVEN_FUNCTIONS):
            card = FunctionCard(func, self._select_mode)
            self.cards[func["key"]] = card
            grid.addWidget(card, i // 3, i % 3)
        right.addLayout(grid)
        right.addStretch(1)

        right_container = QWidget()
        right_container.setLayout(right)
        root.addWidget(right_container, stretch=1)

        # ---- Controller sinyalleri ----
        self.controller.mode_changed.connect(self._on_mode_changed)
        self.controller.target_temp_changed.connect(self.dial.set_target)
        self.controller.current_temp_changed.connect(self._on_current_temp)
        self.controller.running_changed.connect(self._on_running_changed)

        self._select_mode(self.controller.mode, send_command=False)

    def _select_mode(self, mode_key, send_command=True):
        if send_command:
            self.controller.set_mode(mode_key)
        for key, card in self.cards.items():
            card.set_selected(key == mode_key)

    def _on_mode_changed(self, mode_key):
        for key, card in self.cards.items():
            card.set_selected(key == mode_key)
        func = next(f for f in OVEN_FUNCTIONS if f["key"] == mode_key)
        self.mode_label.setText(func["label"])

    def _on_current_temp(self, value):
        self.current_temp_label.setText(f"Anlık: {value}°C")
        self.dial.set_current(value)

    def _on_running_changed(self, running):
        self.start_btn.setText("Durdur" if running else "Pişirmeyi Başlat")
