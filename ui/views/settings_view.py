"""
ui/views/settings_view.py
============================
Cihaz ayarları + seri bağlantı durumu (kart bağlı mı, yoksa simülasyon
modunda mı çalışıyor - geliştirme sırasında çok işe yarıyor).
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt


class ToggleRow(QFrame):
    def __init__(self, label, sub, checked=True, parent=None):
        super().__init__(parent)
        self.setProperty("class", "settingRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 14, 4, 14)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:14px;")
        text_col.addWidget(lbl)
        self.sub_label = QLabel(sub)
        self.sub_label.setProperty("class", "dim")
        text_col.addWidget(self.sub_label)
        layout.addLayout(text_col)
        layout.addStretch(1)

        self.btn = QPushButton()
        self.btn.setProperty("class", "toggle")
        self.btn.setCheckable(True)
        self.btn.setChecked(checked)
        self.btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn)

    def set_sub(self, text):
        self.sub_label.setText(text)


class SettingsView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(4)

        title = QLabel("Ayarlar")
        title.setProperty("class", "title")
        root.addWidget(title)
        root.addSpacing(10)

        root.addWidget(ToggleRow("İç Işık", "Fırın kapısı açıldığında otomatik yansın", True))
        root.addWidget(ToggleRow("Tuş Sesi", "Dokunmatik geri bildirim sesi", True))
        root.addWidget(ToggleRow("Çocuk Kilidi", "Ekranı kazara dokunmaya karşı kilitle", False))

        self.serial_row = ToggleRow("Kontrol Kartı Bağlantısı", "Bağlanıyor...", True)
        self.serial_row.btn.setEnabled(False)
        root.addWidget(self.serial_row)

        root.addStretch(1)

        self.controller.connection_changed.connect(self._on_connection_changed)

    def _on_connection_changed(self, connected, message):
        self.serial_row.set_sub(message)
        self.serial_row.btn.setChecked(connected)
