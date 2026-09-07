"""
ui/icons.py
============
Harici görsel dosyalarına bağımlı olmayan, QPainter ile çizilen ikonlar.

Neden dosya değil de kod ile çizim?
  - Jetson'a dağıtımda eksik/bozuk asset dosyası riski olmaz.
  - Her boyuta/DPI'ya net şekilde ölçeklenir.
  - Fırın fonksiyon sembolleri gerçek fırınlardaki standart piktogramlarla
    birebir aynı mantıkla (üst çizgi, alt çizgi, fan, zigzag ızgara vb.)
    çizilir, bu yüzden kullanıcıya tanıdık gelir.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QPolygonF
from PyQt5.QtCore import Qt, QRectF, QPointF

EMBER = QColor("#e8672c")
GOLD = QColor("#f0a860")
DIM = QColor("#a89f93")
LINE = QColor("#4d5a63")


class OvenFunctionIcon(QWidget):
    """Fırın fonksiyonu piktogramı (Alt, Alt-Üst, Fan, Pizza, Izgara, Maksi Izgara)."""

    def __init__(self, kind: str, size: int = 44, active: bool = False, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.active = active
        self.setFixedSize(size, size)

    def set_active(self, active: bool):
        self.active = active
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        color = EMBER if self.active else DIM
        pen = QPen(color, max(2, w * 0.045))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        margin = w * 0.16
        box = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        p.drawRoundedRect(box, w * 0.06, w * 0.06)

        top_y = box.top() + box.height() * 0.12
        bottom_y = box.bottom() - box.height() * 0.12
        x0, x1 = box.left() + box.width() * 0.12, box.right() - box.width() * 0.12

        if self.kind == "ALT":
            self._thick_line(p, x0, x1, bottom_y, color)

        elif self.kind == "ALT_UST":
            self._thick_line(p, x0, x1, bottom_y, color)
            self._thick_line(p, x0, x1, top_y, color)

        elif self.kind == "ALT_UST_FAN":
            self._thick_line(p, x0, x1, bottom_y, color)
            self._thick_line(p, x0, x1, top_y, color)
            self._fan(p, box.center(), box.width() * 0.16, color)

        elif self.kind == "PIZZA":
            self._thick_line(p, x0, x1, bottom_y, color)
            r = box.width() * 0.16
            c = QPointF(box.center().x(), box.center().y() + box.height() * 0.02)
            pen2 = QPen(color, max(1.5, w * 0.03), Qt.DashLine)
            p.setPen(pen2)
            p.drawEllipse(c, r, r)

        elif self.kind == "GRILL":
            self._zigzag(p, x0, x1, top_y, box.height() * 0.16, color)

        elif self.kind == "MAXI_GRILL":
            self._zigzag(p, x0, x1, top_y, box.height() * 0.16, color)
            self._thick_line(p, x0, x1, bottom_y, color)

        p.end()

    @staticmethod
    def _thick_line(p, x0, x1, y, color):
        pen = QPen(color, 3.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(x0, y), QPointF(x1, y))

    @staticmethod
    def _zigzag(p, x0, x1, y, amp, color):
        pen = QPen(color, 3)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        segments = 4
        width = x1 - x0
        pts = []
        for i in range(segments + 1):
            x = x0 + width * (i / segments)
            yy = y - amp / 2 if i % 2 == 0 else y + amp / 2
            pts.append(QPointF(x, yy))
        p.drawPolyline(QPolygonF(pts))

    @staticmethod
    def _fan(p, center, radius, color):
        pen = QPen(color, 2.2)
        p.setPen(pen)
        p.drawEllipse(center, radius, radius)
        for i in range(3):
            ang = i * 120
            p.save()
            p.translate(center)
            p.rotate(ang)
            p.drawLine(QPointF(0, 0), QPointF(0, -radius * 0.85))
            p.restore()


class NavIcon(QWidget):
    """Sol menü ikonları: home, list (tarifler), clock, gear, mic."""

    def __init__(self, kind: str, size: int = 22, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(size, size)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pen = QPen(QColor("#f5f1ea"), max(1.6, w * 0.09))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)

        if self.kind == "home":
            p.drawPolyline(QPolygonF([
                QPointF(w * 0.12, h * 0.5), QPointF(w * 0.5, h * 0.12), QPointF(w * 0.88, h * 0.5)
            ]))
            p.drawRect(QRectF(w * 0.22, h * 0.46, w * 0.56, h * 0.42))

        elif self.kind == "recipes":
            p.drawRoundedRect(QRectF(w * 0.16, h * 0.1, w * 0.68, h * 0.8), 3, 3)
            for i in range(3):
                yy = h * (0.32 + i * 0.18)
                p.drawLine(QPointF(w * 0.28, yy), QPointF(w * 0.72, yy))

        elif self.kind == "timer":
            p.drawEllipse(QRectF(w * 0.12, h * 0.16, w * 0.76, h * 0.76))
            c = QPointF(w * 0.5, h * 0.54)
            p.drawLine(c, QPointF(w * 0.5, h * 0.32))
            p.drawLine(c, QPointF(w * 0.66, h * 0.6))
            p.drawLine(QPointF(w * 0.4, h * 0.05), QPointF(w * 0.6, h * 0.05))

        elif self.kind == "settings":
            p.drawEllipse(QRectF(w * 0.32, h * 0.32, w * 0.36, h * 0.36))
            for i in range(8):
                p.save()
                p.translate(w * 0.5, h * 0.5)
                p.rotate(i * 45)
                p.drawLine(QPointF(0, -h * 0.36), QPointF(0, -h * 0.46))
                p.restore()

        elif self.kind == "mic":
            p.drawRoundedRect(QRectF(w * 0.38, h * 0.08, w * 0.24, h * 0.46), w * 0.12, w * 0.12)
            p.drawArc(QRectF(w * 0.2, h * 0.28, w * 0.6, h * 0.5), 0, -180 * 16)
            p.drawLine(QPointF(w * 0.5, h * 0.78), QPointF(w * 0.5, h * 0.92))
            p.drawLine(QPointF(w * 0.36, h * 0.92), QPointF(w * 0.64, h * 0.92))

        p.end()
