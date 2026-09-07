"""
ui/widgets/temp_dial.py
=========================
Ana ekrandaki dairesel hedef-sıcaklık kadranı.
Fiziksel fırın düğmelerine gönderme yapan, kor renginde dolan bir yay.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QConicalGradient
from PyQt5.QtCore import Qt, QRectF

import config


class TempDial(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target = config.DEFAULT_TEMP
        self.current = 24
        self.setFixedSize(210, 210)

    def set_target(self, value: int):
        self.target = value
        self.update()

    def set_current(self, value: int):
        self.current = value
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        margin = 14
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        # arka halka
        bg_pen = QPen(QColor("#2a2724"), 13)
        bg_pen.setCapStyle(Qt.RoundCap)
        p.setPen(bg_pen)
        p.drawArc(rect, 0, 360 * 16)

        # değer yayı
        pct = max(0.0, min(1.0, (self.target - config.MIN_TEMP) / (config.MAX_TEMP - config.MIN_TEMP)))
        grad = QConicalGradient(rect.center(), 90)
        grad.setColorAt(0.0, QColor("#f0a860"))
        grad.setColorAt(1.0, QColor("#e8672c"))
        fg_pen = QPen(QColor("#e8672c"), 13)
        fg_pen.setCapStyle(Qt.RoundCap)
        fg_pen.setBrush(grad)
        p.setPen(fg_pen)
        start_angle = 90 * 16
        span_angle = -int(360 * pct * 16)
        p.drawArc(rect, start_angle, span_angle)

        # metin
        p.setPen(QColor("#f0a860"))
        f = p.font()
        f.setFamily("JetBrains Mono")
        f.setPointSize(26)
        f.setBold(True)
        p.setFont(f)
        p.drawText(rect, Qt.AlignCenter, f"{self.target}°")

        p.end()
